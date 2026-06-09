"""
This module creates the UI of the App and calls backend functions from the
project directory for streamline processing of Abandoned Calls Files
"""

import os
import json
import pandas as pd
import customtkinter
import threading
from transform.dedupe_rc_data import remove_rc_duplicates
from main import main as run_tool
from transform.grab_new_deals_id import main as grab_new_deals_id
from user_input.update_pipeline_json import update_pipeline_json_from_xlsx


customtkinter.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme("dark-blue")  # Themes: "blue" (standard), "green", "dark-blue"

# Outside function that will center a new pop up window relative to the main window
def center_new_window(main_window: customtkinter.CTkFrame,
                      new_window: customtkinter.CTkFrame) -> None:

    # Set the geomtry of the new window
    def set_geometry() -> None:

        # Get x and y position of the main window
        main_x = main_window.winfo_rootx()
        main_y = main_window.winfo_rooty()

        # Main window dimensions
        main_width = 800
        main_height = 580

        # Update idle task to avoid bugs in changing geometry
        new_window.update_idletasks()

        # Get the new window dimensions
        new_window_width = new_window.winfo_width()
        new_window_height = new_window.winfo_height()

        # Calculate new the position of the new window so that it is centered
        x = main_x + (main_width - new_window_width) // 2
        y = main_y + (main_height - new_window_height) // 2

        # Apply new position
        new_window.geometry(f"{new_window_width}x{new_window_height}+{int(x)}+{int(y)}")

    # Add delay to avoid bugs in setting new window position
    new_window.after(70, set_geometry)

# Create User Interface Class
class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        """"""""""""""""""""""""
        #   MAIN APP WINDOW    #
        """"""""""""""""""""""""

        # configure window
        self.title("JC Tool v2.0.1")
        self.geometry(self.center_main_window(800, 580))
        self.resizable(False, False)
        self.iconbitmap("misc/tool_icon.ico")

        # configure grid layout (4x4)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_rowconfigure((0, 1, 2), weight=1)



        """"""""""""""""""""""""""""""
        #  INITIALIZE BACKEND DATA   #
        """"""""""""""""""""""""""""""

        # Read pipedrive stages data
        self.pipeline_stages_dict = self.extract_pipedrive_stages()

        # pipeline buttons
        self.pipeline_buttons = {}

        # Variables for local JSON Data
        self.user_desgination, self.conditions_dict = self.read_conditions_designations()



        """"""""""""""""""""""""
        #   RIGHT SIDE FRAME   #
        """"""""""""""""""""""""

        # Create right side frame
        self.conditions_frame = customtkinter.CTkFrame(self, width=280, corner_radius=0)
        self.conditions_frame.grid(row=0, column=1, rowspan=4, sticky="nsew", padx=(5, 0))
        self.conditions_frame.grid_rowconfigure(0, weight=3)
        self.conditions_frame.grid_columnconfigure(0, weight=1)



        """"""""""""""""""""""""
        #    LEFT SIDE FRAME   #
        """"""""""""""""""""""""

        # Create left side frame
        self.sidebar_frame = customtkinter.CTkFrame(self,
                                                    width=140,
                                                    corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure((1,2,3,4,5,6,7,8,9), weight=1)
        self.sidebar_frame.grid_rowconfigure((0,1), weight=4)



        """"""""""""""""""""""""""""""
        #   LEFT SIDE FRAME WIDGETS  #
        """"""""""""""""""""""""""""""

        # Run tool button
        self.run_tool_button = customtkinter.CTkButton(self.sidebar_frame,
                                                       text='RUN TOOL',
                                                       corner_radius=50,
                                                       fg_color='#d99125',
                                                       hover_color='#ae741e',
                                                       text_color='#141414',
                                                       command=self.select_run_option,
                                                       height=80,
                                                       font=customtkinter.CTkFont(size=30,
                                                                                  weight='bold',
                                                                                  family='Roboto Black'))
        self.run_tool_button.grid(row=0, column=0, padx=10, pady=(20,10))

        # Scrollable Pipeline display
        self.pipeline_frame = customtkinter.CTkScrollableFrame(self.sidebar_frame,
                                                               width=120,
                                                               height=200,
                                                               label_text="Pipelines",
                                                               label_anchor="center",
                                                               label_font=customtkinter.CTkFont(
                                                                   family='Roboto Black',
                                                                   weight='bold',
                                                                   size=18))
        self.pipeline_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        # Create Pipeline Buttons
        for key, value in self.user_desgination.items():
            self.create_pipeline_buttons(key, value)

        # Display first pipeline
        self.display_assigned_user_followup(1)

        # Add pipeline button
        self.add_pipeline_button = customtkinter.CTkButton(self.sidebar_frame,
                                                           text='Add Pipeline',
                                                           fg_color='#5b5c5c',
                                                           hover_color='#424343',
                                                           font=customtkinter.CTkFont(weight='normal',
                                                                                      family='Roboto Regular',
                                                                                      size=12),
                                                           command=self.add_pipeline)
        self.add_pipeline_button.grid(row=2, column=0, padx=20, pady=(15, 5), sticky="ew")

        # ✅ Update pipeline button (NEW)
        self.update_pipeline_button = customtkinter.CTkButton(self.sidebar_frame,
                                                            text='Update Pipeline',
                                                            fg_color='#5b5c5c',
                                                            hover_color='#424343',
                                                            font=customtkinter.CTkFont(weight='normal',
                                                                                        family='Roboto Regular',
                                                                                        size=12),
                                                            command=self.update_pipeline)
        self.update_pipeline_button.grid(row=3, column=0, padx=20, pady=5, sticky="ew")

        # Delete pipeline button
        self.delete_pipeline_button = customtkinter.CTkButton(self.sidebar_frame,
                                                              text='Remove Pipeline',
                                                              fg_color='#5b5c5c',
                                                              hover_color='#424343',
                                                              font=customtkinter.CTkFont(weight='normal',
                                                                                         family='Roboto Regular',
                                                                                         size=12),
                                                              command=self.delete_pipeline_window_func)
        self.delete_pipeline_button.grid(row=4, column=0, padx=20, pady=5, sticky="ew")

        # Reset pipeline button
        self.reset_pipeline_button = customtkinter.CTkButton(self.sidebar_frame,
                                                             text='Reset All Pipelines',
                                                             fg_color='#5b5c5c',
                                                             hover_color='#424343',
                                                             command=self.reset_pipeline_values,
                                                             font=customtkinter.CTkFont(weight='normal',
                                                                                        family='Roboto Regular',
                                                                                        size=12))
        self.reset_pipeline_button.grid(row=5, column=0, padx=20, pady=5, sticky="ew")

        # Check all pipeline conditions
        self.check_all_pipeline_conditions_button = customtkinter.CTkButton(self.sidebar_frame,
                                                                            text='Check All Pipelines',
                                                                            fg_color='#5b5c5c',
                                                                            hover_color='#424343',
                                                                            command=lambda: self.display_all_pipeline_conditions(False),
                                                                            font=customtkinter.CTkFont(weight='normal',
                                                                                                       family='Roboto Regular',
                                                                                                       size=12))
        self.check_all_pipeline_conditions_button.grid(row=6, column=0, padx=20, pady=5, sticky="ew")

        # Remove rc duplicates button
        self.remove_rc_duplicate_button = customtkinter.CTkButton(self.sidebar_frame,
                                                                  text="Remove JC Duplicates",
                                                                  fg_color='#5b5c5c',
                                                                  hover_color='#424343',
                                                                  command=self.remove_rc_duplicates,
                                                                  font=customtkinter.CTkFont(weight='normal',
                                                                                             family='Roboto Regular',
                                                                                             size=12))
        self.remove_rc_duplicate_button.grid(row=7, column=0, padx=20, pady=5, sticky="ew")

        # Save data button
        self.save_data_button = customtkinter.CTkButton(self.sidebar_frame,
                                                        text='Save',
                                                        fg_color='#5b5c5c',
                                                        hover_color='#424343',
                                                        command=self.save_pipeline_data,
                                                        font=customtkinter.CTkFont(weight='normal',
                                                                                   family='Roboto Regular',
                                                                                   size=12))
        self.save_data_button.grid(row=8, column=0, padx=20, pady=5, sticky="ew")

        # Sideframe appreance mode
        self.current_appearance_mode = customtkinter.get_appearance_mode()
        self.appearance_mode_label = customtkinter.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=9, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(self.sidebar_frame,
                                                                       values=["System", "Dark", 'Light'],
                                                                       command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=10, column=0, padx=20, pady=(10, 10))


    
    """"""""""""""""""""""""""""""
    #    MAIN FUNCTION METHODS   #
    """"""""""""""""""""""""""""""
    def rebuild_pipeline_buttons(self):
        # Destroy existing pipeline buttons
        for key in list(self.pipeline_buttons.keys()):
            try:
                self.pipeline_buttons[key].destroy()
            except Exception:
                pass
        self.pipeline_buttons = {}

        # Re-create from refreshed self.user_desgination
        for key, value in self.user_desgination.items():
            self.create_pipeline_buttons(key, value)


    def update_pipeline(self) -> None:
        # Prevent multiple runs
        if getattr(self, "_update_pipeline_running", False):
            return
        self._update_pipeline_running = True

        # Disable button while running
        try:
            self.update_pipeline_button.configure(state="disabled")
        except Exception:
            pass

        # Popup: "Updating..."
        self.update_pipeline_window = customtkinter.CTkToplevel(self)
        self.update_pipeline_window.geometry("420x160")
        self.update_pipeline_window.title("Update Pipeline")
        self.update_pipeline_window.attributes("-topmost", True)
        self.update_pipeline_window.resizable(False, False)
        self.update_pipeline_window.grid_columnconfigure(0, weight=1)
        self.update_pipeline_window.grid_rowconfigure(0, weight=1)

        # Make it act like a modal dialog
        try:
            self.update_pipeline_window.transient(self)
            self.update_pipeline_window.grab_set()
        except Exception:
            pass

        # Don't allow closing mid-run (avoids confusion)
        self.update_pipeline_window.protocol("WM_DELETE_WINDOW", lambda: None)

        center_new_window(self, self.update_pipeline_window)

        label = customtkinter.CTkLabel(
            self.update_pipeline_window,
            text="Updating pipeline JSON files...\nPlease wait.",
            font=customtkinter.CTkFont(family="Roboto Regular", size=16)
        )
        label.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Run the update in a thread so UI won't freeze
        threading.Thread(target=self._run_update_pipeline, daemon=True).start()


    def _run_update_pipeline(self) -> None:
        try:
            xlsx_path = "data/conditions_input/Pipedrive Stages - Stages.xlsx"
            out_dir = "data/conditions_input"

            # Clearer error if file is missing
            if not os.path.exists(xlsx_path):
                raise FileNotFoundError(
                    f"Missing required file:\n{xlsx_path}\n\n"
                    f"Make sure the XLSX is in the correct folder."
                )

            # 1) Rebuild JSONs from XLSX
            update_pipeline_json_from_xlsx(
                xlsx_path=xlsx_path,
                out_dir=out_dir,
            )

            # 2) Re-read JSONs into app memory
            self.user_desgination, self.conditions_dict = self.read_conditions_designations()

            # 3) Refresh UI back on the main thread
            self.after(0, self._finish_update_pipeline_success)

        except Exception as e:
            self.after(0, lambda: self._finish_update_pipeline_failed(str(e)))

    def _finish_update_pipeline_success(self):
        # Close "Updating..." window
        if hasattr(self, "update_pipeline_window"):
            try:
                self.update_pipeline_window.destroy()
            except Exception:
                pass

        # Rebuild left pipeline buttons
        self.rebuild_pipeline_buttons()

        # Refresh right panel display (show first pipeline if exists)
        if self.user_desgination:
            first_key = min(self.user_desgination.keys())
            self.display_assigned_user_followup(first_key)

        # Re-enable Update button + clear running flag
        self._update_pipeline_running = False
        try:
            self.update_pipeline_button.configure(state="normal")
        except Exception:
            pass

        # Confirmation popup
        ok = customtkinter.CTkToplevel(self)
        ok.pack_propagate(True)
        ok.attributes("-topmost", True)
        ok.title("Update Pipeline")

        # Modal-ish behavior
        try:
            ok.transient(self)
            ok.grab_set()
        except Exception:
            pass

        center_new_window(self, ok)

        lbl = customtkinter.CTkLabel(ok, text="✅ Pipeline JSON files updated successfully.")
        lbl.pack(padx=20, pady=20)

        btn = customtkinter.CTkButton(ok, text="OK", command=ok.destroy)
        btn.pack(padx=20, pady=(0, 20))

    def _finish_update_pipeline_failed(self, err_msg: str):
        # Close "Updating..." window
        if hasattr(self, "update_pipeline_window"):
            try:
                self.update_pipeline_window.destroy()
            except Exception:
                pass

        # Re-enable Update button + clear running flag
        self._update_pipeline_running = False
        try:
            self.update_pipeline_button.configure(state="normal")
        except Exception:
            pass

        fail = customtkinter.CTkToplevel(self)
        fail.pack_propagate(True)
        fail.attributes("-topmost", True)
        fail.title("Update Pipeline Failed")

        # Modal-ish behavior
        try:
            fail.transient(self)
            fail.grab_set()
        except Exception:
            pass

        center_new_window(self, fail)

        lbl = customtkinter.CTkLabel(
            fail,
            text=f"Update failed.\n\n{err_msg}",
            wraplength=420
        )
        lbl.pack(padx=20, pady=20)

        btn = customtkinter.CTkButton(fail, text="OK", command=fail.destroy)
        btn.pack(padx=20, pady=(0, 20))


    # Change appearance mode of app
    def change_appearance_mode_event(self, new_appearance_mode: str) -> None:
        customtkinter.set_appearance_mode(new_appearance_mode)

    # Create pipeline buttons in left side frame of main window
    def create_pipeline_buttons(self, key: int, value: list) -> None:

        # Create buttons
        button_name = value[0]
        button = customtkinter.CTkButton(self.pipeline_frame,
                                         text=f"{button_name} Pipeline",
                                         command=lambda key=key: self.display_assigned_user_followup(key))
        button.pack(pady=5, padx=5, fill='x', expand=True)
        self.pipeline_buttons[key] = button

    # Add another pipeline in the app
    def add_pipeline(self) -> None:

        # Display pipeline added confirmation
        def show_pipeline_confirmation_window(pipeline_name: str) -> None:

            confirmation_window = customtkinter.CTkToplevel(self)
            confirmation_window.pack_propagate(True)
            center_new_window(self, confirmation_window)
            confirmation_window.title("Pipeline Added")
            label = customtkinter.CTkLabel(confirmation_window, text=f"{pipeline_name} Pipeline has been added successfully")
            label.pack(pady=20, padx=20)
            button = customtkinter.CTkButton(confirmation_window, text="OK", command=confirmation_window.destroy)
            button.pack(pady=20, padx=20)

        pipeline_name_dialog = customtkinter.CTkInputDialog(text="Type in the name of the pipeline: ",
                                                            title="Add Pipeline")
        center_new_window(self, pipeline_name_dialog)
        new_pipeline_name = pipeline_name_dialog.get_input()

        # If input is not blank
        if new_pipeline_name:
            if new_pipeline_name.title() in self.pipeline_stages_dict:

                new_pipeline_name = new_pipeline_name.title()
                new_pipeline_key = len(self.user_desgination) + 1

                button_name = new_pipeline_name
                button = customtkinter.CTkButton(self.pipeline_frame,
                                                text=f"{button_name} Pipeline",
                                                command=lambda key=new_pipeline_key: self.display_assigned_user_followup(key))
                button.pack(pady=5, padx=5, fill='x', expand=True)

                # Update variables and JSON Data
                self.pipeline_buttons[new_pipeline_key] = button
                self.user_desgination[new_pipeline_key] = [new_pipeline_name, "None", "None"]
                self.conditions_dict[new_pipeline_key] = []    

                button.pack(pady=5, padx=5)

                # Prompt confirmation window
                show_pipeline_confirmation_window(new_pipeline_name)

            else:
                # Pop up a CTk window with an error message
                warning_window = customtkinter.CTkToplevel()
                center_new_window(self, warning_window)
                warning_window.attributes('-topmost', True)
                warning_window.title("Add Pipeline")
                
                # Center the pop-up window on the main window
                warning_window.geometry(f"400x130+{self.winfo_rootx()+50}+{self.winfo_rooty()+50}")
                
                # Display the warning message
                warning_label = customtkinter.CTkLabel(warning_window, text=f"Wrong pipeline information.\n{new_pipeline_name.title()} Pipeline is not in Community Minerals Pipedrive Pipelines")
                warning_label.pack(pady=20)
                
                # Add an OK button to close the window
                ok_button = customtkinter.CTkButton(warning_window, text="OK", command=warning_window.destroy)
                ok_button.pack(pady=10)

    # Window pop up for deleting a pipeline
    def delete_pipeline_window_func(self) -> None:
        
        self.delete_pipeline_window = customtkinter.CTkToplevel(self)
        self.delete_pipeline_window.pack_propagate(True)
        center_new_window(self, self.delete_pipeline_window)
        self.delete_pipeline_window.title("Delete Pipeline")
        self.delete_pipeline_window.attributes("-topmost", True)

        label = customtkinter.CTkLabel(self.delete_pipeline_window, text="Select the pipeline that you want to remove: ")
        label.pack(padx=15, pady=15)

        self.delete_selected_pipeline_rb = customtkinter.IntVar()

        for key, value in self.user_desgination.items():
            rb = customtkinter.CTkRadioButton(self.delete_pipeline_window,
                                              text=f"{value[0]} Pipeline",
                                              variable=self.delete_selected_pipeline_rb,
                                              value=key)

            rb.pack(pady=5, padx=5,anchor='w')
        
        ok_delete_button = customtkinter.CTkButton(self.delete_pipeline_window,
                                                  text='Remove Pipeline',
                                                  fg_color='#c94040',
                                                  hover_color='#8c2626',
                                                  command=self.delete_pipeline)
        ok_delete_button.pack(pady=20)
        
    # Delete selected pipeline from the app
    def delete_pipeline(self) -> None:

        key_to_remove = self.delete_selected_pipeline_rb.get()

        if key_to_remove > 0:

            self.delete_pipeline_window.destroy()
            delete_confirmation_window = customtkinter.CTkToplevel(self)
            delete_confirmation_window.pack_propagate(True)
            center_new_window(self, delete_confirmation_window)
            delete_confirmation_window.title("Pipeline Deleted")
            delete_confirmation_window.attributes("-topmost", True)
            label = customtkinter.CTkLabel(delete_confirmation_window,
                                           text=f"{self.user_desgination[key_to_remove][0]} Pipeline has been deleted successfully")
            label.pack(pady=20, padx=20)
            button = customtkinter.CTkButton(delete_confirmation_window, text="OK", command=delete_confirmation_window.destroy)
            button.pack(pady=20, padx=20)

            # Remove buttons for key
            if key_to_remove in self.pipeline_buttons:
                self.pipeline_buttons[key_to_remove].destroy()
                del self.pipeline_buttons[key_to_remove]

                max_key = max(self.pipeline_buttons.keys())
                for key in range(key_to_remove + 1, max_key + 1):
                    self.pipeline_buttons[key - 1] = self.pipeline_buttons.pop(key)

            # Remove pipeline for key
            if key_to_remove in self.user_desgination:
                del self.user_desgination[key_to_remove]

                max_key = max(self.user_desgination.keys())
                for key in range(key_to_remove + 1, max_key + 1):
                    self.user_desgination[key - 1] = self.user_desgination.pop(key)

            # Remove conditions for key
            if key_to_remove in self.conditions_dict:
                del self.conditions_dict[key_to_remove]

                max_key = max(self.conditions_dict.keys())
                for key in range(key_to_remove + 1, max_key + 1):
                    self.conditions_dict[key - 1] = self.conditions_dict.pop(key)

            # Update pipeline display
            for key in self.pipeline_buttons:
                self.pipeline_buttons[key].destroy()

            for key, value in self.user_desgination.items():
                self.create_pipeline_buttons(key, value)

            self.display_assigned_user_followup(key_to_remove - 1)

        # If none was selected from the pipeline delete options
        elif key_to_remove == 0:

            self.delete_pipeline_window.destroy()
            delete_confirmation_window = customtkinter.CTkToplevel(self)
            delete_confirmation_window.pack_propagate(True)
            delete_confirmation_window.geometry("300x150")
            center_new_window(self, delete_confirmation_window)
            delete_confirmation_window.title("Pipeline Deleted")
            delete_confirmation_window.attributes("-topmost", True)
            label = customtkinter.CTkLabel(delete_confirmation_window, text="No pipeline was selected")
            label.pack(pady=20, padx=20)
            button = customtkinter.CTkButton(delete_confirmation_window, text="OK", command=delete_confirmation_window.destroy)
            button.pack(pady=20, padx=20)

    # Reset all pipeline values to defualt settings
    def reset_pipeline_values(self) -> None:

        # Continue reset button function
        def continue_reset() -> None:

            reset_confirmation_window.destroy()

            # Default user designation dictionary
            user_designation = {
                1:  ['Qualifying', 'None', 'None'],
                2:  ['Conversion','None', 'None'],
                3:  ['Underwriting', 'None', 'None'],
                4:  ['Sales Team', 'None', 'None'],
                5:  ['Junior Sales Team', 'None', 'None'],
                6:  ['White Glove', 'None', 'None'],
                7:  ['Fast Close', 'None', 'None'],
                8:  ['PSA', 'None', 'None'],
                9:  ['Diligence', 'None', 'None'],
                10: ['Closing', 'None', 'None']
            }

            # Empty conditions dictionary
            conditions_dict = {
                1:  [],
                2:  [],
                3:  [],
                4:  [],
                5:  [],
                6:  [],
                7:  [],
                8:  [],
                9:  [],
                10: [],
            }

            # Assign the dictionaries to object attribute
            self.user_desgination = user_designation
            self.conditions_dict = conditions_dict
            
            # Delete pipeline buttons
            for key in self.pipeline_buttons:
                self.pipeline_buttons[key].destroy()

            # Re-create Pipeline Buttons
            for key, value in self.user_desgination.items():
                self.create_pipeline_buttons(key, value)

            self.display_assigned_user_followup(1)

            success_reset_window = customtkinter.CTkToplevel(self)
            success_reset_window.pack_propagate(True)
            center_new_window(self, success_reset_window)
            success_reset_window.attributes('-topmost', True)
            success_reset_window.title('Pipeline Reset Successful')
            success_reset_label = customtkinter.CTkLabel(success_reset_window,
                                                         text="All pipelines were successfully reset")
            success_reset_label.pack(padx=20, pady=20)
            success_ok_button = customtkinter.CTkButton(success_reset_window,
                                                        text="OK",
                                                        command=success_reset_window.destroy)
            success_ok_button.pack(padx=20, pady=20)


        # Cancel reset button function
        def cancel_reset() -> None:
            reset_confirmation_window.destroy()


        reset_confirmation_window = customtkinter.CTkToplevel(self)
        center_new_window(self, reset_confirmation_window)
        reset_confirmation_window.pack_propagate(True)
        reset_confirmation_window.attributes("-topmost", True)
        reset_confirmation_window.title('Reset All Pipelines')
        reset_label = customtkinter.CTkLabel(reset_confirmation_window,
                                             text="This will reset all pipeline values and conditions, are you sure?")
        reset_label.grid(row=0, padx=20, pady=(20, 10), sticky="nsew")

        # Reset confirmation window
        reset_confirm_button_frame = customtkinter.CTkFrame(reset_confirmation_window,
                                                            fg_color="transparent")
        reset_confirm_button_frame.grid(row=1, padx=5, pady=5, sticky="nsew")
        reset_confirm_button_frame.grid_columnconfigure((0,1), weight=1)

        # Continue button
        reset_confirm_button = customtkinter.CTkButton(reset_confirm_button_frame,
                                                       text="Reset All Pipelines",
                                                       command=continue_reset)
        reset_confirm_button.grid(row=0, column=0, padx=5, pady=10, stick="nsew")

        # Cancel button
        reset_cancel_button = customtkinter.CTkButton(reset_confirm_button_frame,
                                                       text="Cancel",
                                                       command=cancel_reset)
        reset_cancel_button.grid(row=0, column=1, padx=5, pady=10, stick="nsew")

    # Display all pipeline values and stage conditions of all pipelines
    def display_all_pipeline_conditions(self, check_run: bool) -> None:

        pipeline_conditions_window = customtkinter.CTkToplevel(self)
        pipeline_conditions_window.attributes("-topmost", True)
        pipeline_conditions_window.title("All Pipeline Conditions")
        pipeline_conditions_window.geometry("1280x600")
        pipeline_conditions_window.resizable(False, False)
        pipeline_conditions_window.grid_rowconfigure(0, weight=1)
        pipeline_conditions_window.grid_columnconfigure(0, weight=1)
        center_new_window(self, pipeline_conditions_window)

        horizontal_scrollbar_frame = customtkinter.CTkScrollableFrame(pipeline_conditions_window,
                                                                      orientation="horizontal")
        horizontal_scrollbar_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        horizontal_scrollbar_frame.grid_rowconfigure(0, weight=1)
        
        column_number = 0

        # If triggered by Run Tool, add a button
        if check_run:
            run_button = customtkinter.CTkButton(pipeline_conditions_window,
                                                text="RUN TOOL",
                                                corner_radius=50,
                                                fg_color='#d99125',
                                                hover_color='#ae741e',
                                                text_color='#141414',
                                                command=lambda:self.confirm_run_tool(pipeline_conditions_window),
                                                font=customtkinter.CTkFont(
                                                    family="Roboto Black",
                                                    size=30,
                                                    weight="bold"
                                                ))
            run_button.grid(row=1, column=0, padx=20, pady=10, sticky="ns")

        # Create vertical pipeline frames
        for key in self.conditions_dict:

            '''
            Pipeline-Conditions frame
            '''
            pipeline_conditions_frame = customtkinter.CTkFrame(horizontal_scrollbar_frame,
                                                               border_width=2)
            pipeline_conditions_frame_label = customtkinter.CTkLabel(pipeline_conditions_frame,
                                                                    text=f"{self.user_desgination[key][0]} Pipeline",
                                                                    font=customtkinter.CTkFont(
                                                                        family="Roboto Black",
                                                                        size=35))
            pipeline_conditions_frame_label.grid(row=0, column=0, padx=5, pady=(20, 5), sticky="nsew")
            pipeline_conditions_frame.grid(row=0, column=column_number, padx=10, pady=10, ipadx=5, ipady=5, sticky="nsew")
            pipeline_conditions_frame.grid_columnconfigure(0, weight=1)
            pipeline_conditions_frame.grid_rowconfigure((0,1,2), weight=0)
            pipeline_conditions_frame.grid_rowconfigure(3, weight=3)

            '''
            Conditions scrollable frame
            '''
            conditions_frame = customtkinter.CTkScrollableFrame(pipeline_conditions_frame,
                                                                label_text="Stage Conditions",
                                                                label_font=customtkinter.CTkFont(
                                                                            family='Roboto Black',
                                                                            size=25))
            conditions_frame.grid(row=3, column=0, padx=5, pady=5, sticky="nsew")

            '''
            Pipeline-Condition Labels
            '''

            # Pipeline Follow Up
            pipeline_follow_up_label = customtkinter.CTkLabel(pipeline_conditions_frame,
                                                            text=f"{self.user_desgination[key][1]}",
                                                            anchor="center",
                                                            font=customtkinter.CTkFont(
                                                                family='Roboto Medium',
                                                                size=18))
            pipeline_follow_up_label.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

            # Pipeline Assigned User
            pipeline_user_label = customtkinter.CTkLabel(pipeline_conditions_frame,
                                                        text=f"{self.user_desgination[key][2]}",
                                                        anchor="center",
                                                        font=customtkinter.CTkFont(
                                                            family='Roboto Medium',
                                                            size=18))
            pipeline_user_label.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

            column_number += 1

            # If pipeline conditions is empty
            if len(self.conditions_dict[key]) == 0:

                no_conditions_label = customtkinter.CTkLabel(conditions_frame,
                                                            text="There are no Stage Conditions for this pipeline",
                                                            anchor="center",
                                                            wraplength=240,
                                                            font=customtkinter.CTkFont(
                                                                family='Roboto Medium',
                                                                size=15))
                no_conditions_label.pack(padx=10, pady=5)

            # If there is atleast 1 pipeline condition
            elif len(self.conditions_dict[key]) > 0:
                for condition in self.conditions_dict[key]:
                    for stage, value in condition.items():

                        # Per stage condition horizontal frame
                        per_stage_frame = customtkinter.CTkFrame(conditions_frame,
                                                                    border_width=3,
                                                                    corner_radius=25)
                        per_stage_frame.pack(padx=10, pady=5, fill="x", anchor="center")
                        per_stage_frame.grid_columnconfigure(0, weight=1)

                        # Stage name
                        live_stage_label = customtkinter.CTkLabel(per_stage_frame,
                                                                text=stage,
                                                                anchor="center",
                                                                wraplength=180,
                                                                font=customtkinter.CTkFont(
                                                                    family="Roboto Medium",
                                                                    size=16,
                                                                    weight="normal"
                                                                ))
                        live_stage_label.grid(row=0, column=0, padx=10, pady=5)

                        # Stage Follow Up
                        live_fu_label = customtkinter.CTkLabel(per_stage_frame,
                                                            text=value[1],
                                                            anchor="center",
                                                            wraplength=180,
                                                            font=customtkinter.CTkFont(
                                                                family="Roboto Medium",
                                                                size=16,
                                                                weight="normal"
                                                            ))
                        live_fu_label.grid(row=1, column=0, padx=10, pady=5)

                        # Stage Assigned User
                        live_user_label = customtkinter.CTkLabel(per_stage_frame,
                                                                text=value[2],
                                                                anchor="center",
                                                                wraplength=180,
                                                                font=customtkinter.CTkFont(
                                                                    family="Roboto Medium",
                                                                    size=16,
                                                                    weight="normal"
                                                                ))
                        live_user_label.grid(row=2, column=0, padx=10, pady=5)

    # Save pipeline data
    def save_pipeline_data(self) -> None:

        # If confirm is pressed
        def confirmed_save() -> None:

            # Remove top window
            confirm_save_data_window.destroy()

            # Define JSON Data Path
            conditions_path = 'data/conditions_input/conditions_dict.json'
            user_designation_path = 'data/conditions_input/user_designation.json'

            # Save dictionary as JSON Data
            with open(conditions_path, 'w', encoding='utf-8') as conditions_json_file:
                json.dump(self.conditions_dict, conditions_json_file)

            # Overwrite user_designation.json
            with open(user_designation_path, 'w', encoding='utf-8') as designations_json_file:
                json.dump(self.user_desgination, designations_json_file)

            # Display save confirmation
            save_confirmation_window = customtkinter.CTkToplevel(self)
            center_new_window(self, save_confirmation_window)
            save_confirmation_window.pack_propagate(True)
            save_confirmation_window.attributes('-topmost', True)
            save_confirmation_window.title('Save pipeline data')
            save_confirmation_window_label = customtkinter.CTkLabel(save_confirmation_window,
                                                                    text="Pipeline and Conditions data was successfully saved")
            save_confirmation_window_label.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
            save_confirmation_window_button = customtkinter.CTkButton(save_confirmation_window,
                                                                    text="OK",
                                                                    command=save_confirmation_window.destroy)
            save_confirmation_window_button.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")
        
        # Ask user if confirm to save the JSON Data
        confirm_save_data_window = customtkinter.CTkToplevel()
        confirm_save_data_window.title("Save Pipelines and Conditions")
        confirm_save_data_window.attributes("-topmost", True)
        confirm_save_data_window.geometry("400x150")
        confirm_save_data_window.grid_rowconfigure((0,1), weight=1)
        confirm_save_data_window.grid_columnconfigure(0, weight=1)
        center_new_window(self, confirm_save_data_window)
        confirm_save_data_window_label = customtkinter.CTkLabel(confirm_save_data_window,
                                                                text="Save all pipeline and condition values?")
        confirm_save_data_window_label.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        confirm_button_frame = customtkinter.CTkFrame(confirm_save_data_window, fg_color="transparent")
        confirm_button_frame.grid(row=1, column=0, padx=10, pady=(0,5), stick="nsew")
        confirm_button_frame.grid_columnconfigure((0,1), weight=1)
        confirm_button_frame.grid_rowconfigure(0, weight=1)
        confirm_button = customtkinter.CTkButton(confirm_button_frame,
                                                 text="Confirm",
                                                 command=confirmed_save)
        confirm_button.grid(row=0, column=0, padx=10, pady=5)
        cancel_button = customtkinter.CTkButton(confirm_button_frame,
                                                text="Cancel",
                                                command=confirm_save_data_window.destroy)
        cancel_button.grid(row=0, column=1, padx=10, pady=5)
        
    # Edit Pipeline Follow Up Task and Assigned User
    def edit_pipeline_data(self, key: int=1) -> None:

        # Disable highlighting of option
        def disable_selection(event) -> str:
            return "break"
        
        # Function for selecting follow up task
        def on_follow_up_select(*args) -> None:

            # Get the selected follow up
            type_in_selected = follow_up_selected.get()

            # If user selected custom follow up
            if type_in_selected == "Type in the follow up task":
                fu_entry = customtkinter.CTkInputDialog(text="Enter follow up here",
                                                        title="Follow Up")
                fu_entry.pack_propagate(True)
                center_new_window(self,fu_entry)
                user_fu_input = fu_entry.get_input()

                # If entry field not empty
                if user_fu_input:
                    self.pipeline_fu_name = user_fu_input
                    live_fu_label.configure(text=self.pipeline_fu_name)

            # If user selected a follow up from the default list
            else:
                self.pipeline_fu_name = type_in_selected
                live_fu_label.configure(text=self.pipeline_fu_name)

        # Function for selecting assigned user
        def on_assign_user_select(*args) -> None:

            # Get selected assigned user
            type_in_selected = assign_user_selected.get()

            # If user selected custom assigned user
            if type_in_selected == "Type in the assigned user":
                user_entry = customtkinter.CTkInputDialog(text="Enter assigned user here",
                                                          title="Assigned User")
                user_entry.pack_propagate(True)
                center_new_window(self, user_entry)
                user_assigned_input = user_entry.get_input()

                # If entry field not empty
                if user_assigned_input:
                    self.pipeline_user_name = user_assigned_input
                    live_user_label.configure(text=self.pipeline_user_name)

            # If user selected an assigned user from the default list
            else:
                self.pipeline_user_name = type_in_selected
                live_user_label.configure(text=self.pipeline_user_name)

        # Function will apply all the changes to the object attribute dictionary
        def edit_pipeline_func() -> None:

            # self.conditions_dict[key].append({self.stage_name: ['Deal - Stage',
            #                                                     self.fu_name,
            #                                                     self.user_name]})
            pipeline_values = self.user_desgination[key]

            # If user input for follow up and assigned user is not empty
            if self.pipeline_fu_name != '' and self.pipeline_user_name != '':
                pipeline_values[1] = self.pipeline_fu_name
                pipeline_values[2] = self.pipeline_user_name
                self.display_assigned_user_followup(key)
                add_stage_window.destroy()

            # If user input is empty to either of follow up or assigned
            else:
                # Pop up a CTk window with an error message
                warning_window = customtkinter.CTkToplevel()
                center_new_window(self, warning_window)
                warning_window.attributes('-topmost', True)
                add_stage_window.attributes('-topmost', False)
                warning_window.title("Incomplete Information")
                
                # Center the pop-up window on the main window
                warning_window.geometry(f"300x120+{self.winfo_rootx()+50}+{self.winfo_rooty()+50}")
                
                # Display the warning message
                warning_label = customtkinter.CTkLabel(warning_window, text="Incomplete Infromation. Please try again")
                warning_label.pack(pady=20)
                
                # Add an OK button to close the window
                ok_button = customtkinter.CTkButton(warning_window, text="OK", command=warning_window.destroy)
                ok_button.pack(pady=10)

        # Follow Up option list
        follow_up_list = [
            "CT - Abandoned Call Follow Up",
            "AA - Abandoned Call Follow Up",
            "CA - Abandoned Call Follow Up",
            "PD - Abandoned Call Follow Up",
            "Type in the follow up task"
        ]

        # Assgined User option list
        assigned_user_list = [
            "Deal Owner",
            "CA Tracking Flag",
            "Type in the assigned user"
        ]

        # Default pipeline follow up and assigned user
        self.pipeline_fu_name = ''
        self.pipeline_user_name = ''

        # Add stage window
        add_stage_window = customtkinter.CTkToplevel(self)
        add_stage_window.geometry("500x280")
        add_stage_window.resizable(False, False)
        add_stage_window.pack_propagate(True)
        center_new_window(self, add_stage_window)

        add_stage_window.attributes('-topmost', True)
        add_stage_window.title(f"Edit {self.user_desgination[key][0]} Pipeline")
        add_stage_window.grid_columnconfigure(0, weight=1)
        add_stage_window.grid_rowconfigure(1, weight=1)
        add_stage_buttons_frame = customtkinter.CTkFrame(add_stage_window)
        add_stage_buttons_frame.grid(row=0, column=0, padx=20, pady=10, sticky="nsew")
        add_stage_buttons_frame.grid_columnconfigure(1, weight=1)

        # Follow Up Option Menu
        follow_up_selected = customtkinter.StringVar(value="Select a follow up")
        follow_up_selected.trace_add("write", on_follow_up_select)
        follow_up_label = customtkinter.CTkLabel(add_stage_buttons_frame,
                                                 text="Follow Up")
        follow_up_label.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        follow_up_menu = customtkinter.CTkOptionMenu(add_stage_buttons_frame,
                                                     values=follow_up_list,
                                                     variable=follow_up_selected,
                                                     anchor="center")
        follow_up_menu.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        follow_up_menu.bind("<Button-1>", disable_selection)

        # Assigned User Option Menu
        assign_user_selected = customtkinter.StringVar(value="Select a user")
        assign_user_selected.trace_add("write", on_assign_user_select)
        assigned_user_label = customtkinter.CTkLabel(add_stage_buttons_frame,
                                                     text="Assigned User")
        assigned_user_label.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        assigned_user_menu = customtkinter.CTkOptionMenu(add_stage_buttons_frame,
                                                         values=assigned_user_list,
                                                         variable=assign_user_selected,
                                                         anchor="center")
        assigned_user_menu.grid(row=2, column=1, padx=10, pady=10, sticky="nsew")
        assigned_user_menu.bind("<Button-1>", disable_selection)

        # Frame for live selected follow up and assigned user labels
        live_modified_stage_frame = customtkinter.CTkFrame(add_stage_window,
                                                           height=600,
                                                           width=400,
                                                           border_width=2,
                                                           corner_radius=30)
        live_modified_stage_frame.grid(row=1, column=0, padx=20, pady=5, stick="nsew")
        live_modified_stage_frame.grid_rowconfigure((0,1), weight=1)
        live_modified_stage_frame.grid_columnconfigure(0, weight=1)

        # Live selected follow up label
        live_fu_label = customtkinter.CTkLabel(live_modified_stage_frame,
                                               text=self.user_desgination[key][1],
                                               font=customtkinter.CTkFont(
                                                   family="Roboto Medium",
                                                   size=20,
                                                   weight="bold"
                                               ))
        live_fu_label.grid(row=0, column=0, padx=10)

        # Live selected assigned user label
        live_user_label = customtkinter.CTkLabel(live_modified_stage_frame,
                                                 text=self.user_desgination[key][2],
                                                 font=customtkinter.CTkFont(
                                                     family="Roboto Medium",
                                                     size=20,
                                                     weight="bold"
                                                ))
        live_user_label.grid(row=1, column=0, padx=10)

        # Add button
        stage_submit_button = customtkinter.CTkButton(add_stage_window,
                                                      text="Confirm",
                                                      corner_radius=50,
                                                      fg_color="#38753e",
                                                      hover_color="#2c5c31",
                                                      command=edit_pipeline_func,
                                                      font=customtkinter.CTkFont(
                                                          family="Roboto Regular",
                                                          size=15))
        stage_submit_button.grid(row=2, column=0, padx=10, pady=(5, 10))

    # Add a stage condition for a selected pipeline key
    def add_stage_condition(self, key: int=1) -> None:

        # Create stage buttons
        def create_buttons(
                parent: customtkinter.CTkFrame,
                buttons: list,
                items: list,
                window: customtkinter.CTkFrame) -> None:

            # Remove existing buttons
            for button in buttons:
                button.destroy()
            buttons.clear()

            # Add buttons to the scrollable frame
            for item in items:
                button = customtkinter.CTkButton(parent, text=item, command=lambda i=item: on_button_click(i, window))
                button.pack(pady=5, padx=10, fill="x")
                buttons.append(button)

        # Filter stage buttons based on input field
        def filter_items(
                event,
                search_entry: customtkinter.CTkEntry,
                all_items: list,
                buttons: list,
                parent: customtkinter.CTkFrame,
                window: customtkinter.CTkFrame) -> None:
            
            # Get text entry and lower
            query = search_entry.get().lower()

            # If the search entry is empty or last character is deleted, show all items
            if query == "" or len(query) == 1:
                items = all_items[:]

            # Filter items based on the query
            else:
                items = [item for item in all_items if query in item.lower()]
            
            # Update displayed stage buttons
            create_buttons(parent, buttons, items, window)

        # Disable select all or ctrl + a in input field because this causes bug and lag
        def disable_ctrl_a(event) -> str:
            return "break"

        # Function upon clicking a stage button
        def on_button_click(item: str, window: customtkinter.CTkFrame) -> None:

            # If button is Offer Ready or Offer Ready - Small
            if item in ["Offer Ready", "Offer Ready - Small"]:

                # Invoke Offer Ready Function and pass the selected stage
                offer_ready_date(item, window, live_stage_label)
            
            # If not Offer Ready or Offer Ready - Small
            else:

                # Assign the Stage Name to be the selected stage button
                self.stage_name = item

                # Update live stage name label
                live_stage_label.configure(text=item)     
                window.destroy()

        # Disable highlighting by holding left click in option menu to avoid lags and bugs
        def disable_selection(event) -> str:
            return "break"
        
        # Function upon selecting a follow up for a stage
        def on_follow_up_select(*args) -> None:
            type_in_selected = follow_up_selected.get()

            # If user selected custom follow up task
            if type_in_selected == "Type in the follow up task":
                fu_entry = customtkinter.CTkInputDialog(text="Enter follow up here",
                                                        title="Follow Up")
                fu_entry.pack_propagate(True)
                center_new_window(self,fu_entry)
                user_fu_input = fu_entry.get_input()

                # If input field is not empty
                if user_fu_input:
                    self.fu_name = user_fu_input
                    live_fu_label.configure(text=self.fu_name)

            # If user selected default follow up task from the list
            else:
                self.fu_name = type_in_selected
                live_fu_label.configure(text=self.fu_name)

        # Function upon selecting an assigned user for a stage
        def on_assign_user_select(*args) -> None:
            type_in_selected = assign_user_selected.get()

            # If user selected custom assigned user
            if type_in_selected == "Type in the assigned user":
                user_entry = customtkinter.CTkInputDialog(text="Enter assigned user here",
                                                          title="Assigned User")
                user_entry.pack_propagate(True)
                center_new_window(self, user_entry)
                user_assigned_input = user_entry.get_input()

                # If input field is not empty
                if user_assigned_input:
                    self.user_name = user_assigned_input
                    live_user_label.configure(text=self.user_name)

            # If user selected default assigned user from the list
            else:
                self.user_name = type_in_selected
                live_user_label.configure(text=self.user_name)

        # Function for displaying all stages available for a specific pipeline using key
        def select_stage(key: int) -> None:

            # List of items for the dropdown menu
            all_items = self.pipeline_stages_dict[self.user_desgination[key][0]]
            items = all_items[:]
            # all_items = [f"Item {i}" for i in range(1, 21)]
            # items = all_items[:]
            buttons = []

            # Integrate the scrollable dropdown menu into the CTkToplevel window
            select_stage_window = customtkinter.CTkToplevel(add_stage_window)
            select_stage_window.title("Select Stage")
            select_stage_window.geometry("500x500")
            select_stage_window.attributes("-topmost", True)
            add_stage_window.attributes("-topmost", False)
            select_stage_window.resizable(False, True)
            scrollable_frame = customtkinter.CTkScrollableFrame(select_stage_window)
            scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
            center_new_window(self, select_stage_window)

            # Create a search entry inside the scrollable frame
            search_entry = customtkinter.CTkEntry(scrollable_frame, placeholder_text="Search...")
            search_entry.pack(pady=10, padx=10, fill="x")
            search_entry.bind("<Return>", lambda event: filter_items(event,
                                                                     search_entry,
                                                                     all_items,
                                                                     buttons,
                                                                     scrollable_frame,
                                                                     select_stage_window))  # Bind the Enter key to the search function
            search_entry.bind("<BackSpace>", lambda event: filter_items(event,
                                                                        search_entry,
                                                                        all_items,
                                                                        buttons,
                                                                        scrollable_frame,
                                                                        select_stage_window))  # Bind the Backspace key to the search function
            search_entry.bind("<Control-a>", disable_ctrl_a)  # Disable Ctrl + A

            # Create initial stage buttons
            create_buttons(scrollable_frame, buttons, all_items, select_stage_window)

        # Function that will add all input values by user to object attribute dictionaries
        def add_stage_func() -> None:

            # If none of the stage name, follow up, or assigned user is empty
            if self.stage_name != '' and self.fu_name != '' and self.user_name != '':

                # Add the condition and update pipeline condition dictionary
                self.conditions_dict[key].append({self.stage_name: ['Deal - Stage',
                                                                    self.fu_name,
                                                                    self.user_name]})
                self.display_assigned_user_followup(key)
                add_stage_window.destroy()
            
            # If any of them are empty
            else:

                # Pop up a CTk window with an error message
                warning_window = customtkinter.CTkToplevel()
                center_new_window(self, warning_window)
                warning_window.attributes('-topmost', True)
                add_stage_window.attributes('-topmost', False)
                warning_window.title("Incomplete Information")
                
                # Center the pop-up window on the main window
                warning_window.geometry(f"300x120+{self.winfo_rootx()+50}+{self.winfo_rooty()+50}")
                
                # Display the warning message
                warning_label = customtkinter.CTkLabel(warning_window, text="Incomplete Infromation. Please try again")
                warning_label.pack(pady=20)
                
                # Add an OK button to close the window
                ok_button = customtkinter.CTkButton(warning_window, text="OK", command=warning_window.destroy)
                ok_button.pack(pady=10)

        # Function Offer Ready or Offer Ready - Small Stages
        def offer_ready_date(
                item: str,
                window: customtkinter.CTkFrame,
                label: customtkinter.CTkLabel) -> None:

            # Updates states of buttons
            def update_states(*args) -> None:

                # If filter by Offer Ready Date, activate buttons
                if offer_ready_var.get() == "1":
                    state = "normal"

                # If not filter by Offer Ready Date, disable buttons
                else:
                    state = "disabled"
                    selected_operator.set("")
                    offer_ready_days_entry.delete(0, "end")

                # Update button states
                greater_than_operator.configure(state=state)
                less_than_operator.configure(state=state)
                offer_ready_days_entry.configure(state=state)

            # Function that will modify the Offer Ready Stage
            def confirm_offer_ready() -> None:

                # If not filter by Offer Ready Date, return Offer Ready
                if offer_ready_var.get() == "0":
                    self.stage_name = item
                    label.configure(text=self.stage_name)
                    offer_ready_date_window.destroy()
                    window.destroy()

                # If filter by Offer Ready Date, add days and operator
                elif offer_ready_var.get() == "1":
                    days = offer_ready_days_entry.get()
                    operator = selected_operator.get()

                    # If valid operator and days
                    if (days.isdigit() and int(days) != 0) and (operator in [">", "<"]):
                        self.stage_name = f"{item} {operator} {days}"
                        label.configure(text=self.stage_name)
                        offer_ready_date_window.destroy()
                        window.destroy()

                    # If not valid operator or days
                    else:
                        invalid_input_window = customtkinter.CTkToplevel()
                        invalid_input_window.pack_propagate(True)
                        invalid_input_window.attributes("-topmost", True)
                        invalid_input_window.title("Invalid Input")
                        invalid_input_window.geometry("300x200")
                        offer_ready_date_window.attributes("-topmost", False)
                        center_new_window(self, invalid_input_window)
                        invalid_input_label = customtkinter.CTkLabel(invalid_input_window, text="Invalid input. Please try again")
                        invalid_input_label.pack(fill="x", expand=True, padx=10, pady=10)
                        invalid_input_button = customtkinter.CTkButton(invalid_input_window,
                                                                       text="OK",
                                                                       command=invalid_input_window.destroy)
                        invalid_input_button.pack(padx=10, pady=10)

            # Pop up Offer Ready Date window
            offer_ready_date_window = customtkinter.CTkToplevel()
            offer_ready_date_window.attributes('-topmost', True)
            window.attributes('-topmost', False)
            offer_ready_date_window.grid_columnconfigure(0, weight=1)
            offer_ready_date_window.resizable(False, False)
            offer_ready_date_window.geometry("345x225")
            center_new_window(self, offer_ready_date_window)

            # Assign Display Text
            if item == 'Offer Ready':
                display_text = item
            display_text = item

            # Assign variable for selection of filtering by offer ready date or not
            offer_ready_var = customtkinter.StringVar()
            offer_ready_var.set("0")
            check_box_frame = customtkinter.CTkFrame(offer_ready_date_window,
                                                     fg_color="transparent")
            check_box_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

            # Check box for filtering by offer ready date or not
            offer_ready_date_check_box = customtkinter.CTkCheckBox(check_box_frame,
                                                                    variable=offer_ready_var,
                                                                    text="Yes")
            offer_ready_date_check_box.grid(row=0, column=1, padx=(50, 10), pady=10)

            # Label for offer ready date checkbox
            offer_ready_date_label = customtkinter.CTkLabel(check_box_frame,
                                                            text=f"Filter by {display_text} Date")
            offer_ready_date_label.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

            # Variable for selected operator
            selected_operator = customtkinter.StringVar()
            radio_buttons_frame = customtkinter.CTkFrame(offer_ready_date_window,
                                                         fg_color="transparent")
            radio_buttons_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
            radio_buttons_frame.grid_columnconfigure((1,2), weight=1)

            # Radio buttons for operators
            greater_than_operator = customtkinter.CTkRadioButton(radio_buttons_frame,
                                                                 text=" >",
                                                                 variable=selected_operator,
                                                                 value=">",
                                                                 state="disable",
                                                                 font=customtkinter.CTkFont(
                                                                     family="Roboto Black",
                                                                     size=18
                                                                 ))
            greater_than_operator.grid(row=0, column=1, padx=(50,0), pady=10, sticky="nsew")
            less_than_operator = customtkinter.CTkRadioButton(radio_buttons_frame,
                                                              text=" <",
                                                              variable=selected_operator,
                                                              value="<",
                                                              state="disable",
                                                              font=customtkinter.CTkFont(
                                                                     family="Roboto Black",
                                                                     size=18
                                                                 ))
            less_than_operator.grid(row=0, column=2, padx=(5,0), pady=10, sticky="nsew")
            operator_label = customtkinter.CTkLabel(radio_buttons_frame,text="Select an Operator")
            operator_label.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

            # Entry field for typing in days of filtering
            entry_frame = customtkinter.CTkFrame(offer_ready_date_window,
                                                     fg_color="transparent")
            entry_frame.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")
            offer_ready_days_entry = customtkinter.CTkEntry(entry_frame,
                                                            placeholder_text="Type here",
                                                            state="disable",)
            offer_ready_days_entry.grid(row=2, column=1, padx=10, pady=10, sticky="nsew")

            # Label for entry field
            offer_ready_entry_label = customtkinter.CTkLabel(entry_frame,
                                                                text="How many days difference")
            offer_ready_entry_label.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

            # Update states of radio buttons and entry field
            offer_ready_var.trace("w", update_states)

            # Button for adding the Offer Ready to the selected stage
            offer_ready_confirm_button = customtkinter.CTkButton(offer_ready_date_window,
                                                                 text="Confirm",
                                                                 fg_color="#38753e",
                                                                 hover_color="#2c5c31",
                                                                 command=confirm_offer_ready)
            offer_ready_confirm_button.grid(row=3, column=0, padx=10, pady=(0, 20), sticky="ns")
        
        # Follow up menu list
        follow_up_list = [
            "CT - Abandoned Call Follow Up",
            "AA - Abandoned Call Follow Up",
            "CA - Abandoned Call Follow Up",
            "PD - Abandoned Call Follow Up",
            "Type in the follow up task"
        ]

        # Assigned user menu list
        assigned_user_list = [
            "Deal Owner",
            "CA Tracking Flag",
            "Type in the assigned user"
        ]

        # Object attributes for stage, follow up, and assigned user
        self.stage_name = ''
        self.fu_name = ''
        self.user_name = ''

        # Add stage window
        add_stage_window = customtkinter.CTkToplevel(self)
        add_stage_window.geometry("600x400")
        add_stage_window.resizable(False, True)
        add_stage_window.pack_propagate(True)
        center_new_window(self, add_stage_window)

        add_stage_window.attributes('-topmost', True)
        add_stage_window.title(f"Add Stage Condition to {self.user_desgination[key][0]} Pipeline")
        add_stage_window.grid_columnconfigure(0, weight=1)
        add_stage_window.grid_rowconfigure(1, weight=1)
        add_stage_buttons_frame = customtkinter.CTkFrame(add_stage_window)
        add_stage_buttons_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        add_stage_buttons_frame.grid_columnconfigure(1, weight=1)

        # Add stage options label
        add_stage_label = customtkinter.CTkLabel(add_stage_buttons_frame,
                                                 text="Pipeline Stage")
        add_stage_label.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Add stage
        add_stage_button = customtkinter.CTkButton(add_stage_buttons_frame,
                                                   text="Click to select a stage",
                                                   command= lambda pipeline_key=key: select_stage(pipeline_key))
        add_stage_button.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        # Follow up
        follow_up_selected = customtkinter.StringVar(value="Select a follow up")
        follow_up_selected.trace_add("write", on_follow_up_select)
        follow_up_label = customtkinter.CTkLabel(add_stage_buttons_frame,
                                                 text="Follow Up")
        follow_up_label.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        # Follow up list menu
        follow_up_menu = customtkinter.CTkOptionMenu(add_stage_buttons_frame,
                                                     values=follow_up_list,
                                                     variable=follow_up_selected,
                                                     anchor="center")
        follow_up_menu.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        follow_up_menu.bind("<Button-1>", disable_selection)

        # Assigned user
        assign_user_selected = customtkinter.StringVar(value="Select a user")
        assign_user_selected.trace_add("write", on_assign_user_select)
        assigned_user_label = customtkinter.CTkLabel(add_stage_buttons_frame,
                                                     text="Assigned User")
        assigned_user_label.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

        # Assigned user list menu
        assigned_user_menu = customtkinter.CTkOptionMenu(add_stage_buttons_frame,
                                                         values=assigned_user_list,
                                                         variable=assign_user_selected,
                                                         anchor="center")
        assigned_user_menu.grid(row=2, column=1, padx=10, pady=10, sticky="nsew")
        assigned_user_menu.bind("<Button-1>", disable_selection)

        # Live stage name, follow up, and assigned user frame
        live_modified_stage_frame = customtkinter.CTkFrame(add_stage_window,
                                                           height=600,
                                                           width=400,
                                                           border_width=2,
                                                           corner_radius=30)
        live_modified_stage_frame.grid(row=1, column=0, padx=20, pady=(0, 20), stick="nsew")
        live_modified_stage_frame.grid_rowconfigure((0,1,2), weight=1)
        live_modified_stage_frame.grid_columnconfigure(0, weight=1)

        # Live stage labels
        live_stage_label = customtkinter.CTkLabel(live_modified_stage_frame,
                                                  text='No stage selected',
                                                  font=customtkinter.CTkFont(
                                                      family="Roboto Medium",
                                                      size=20,
                                                      weight="bold"
                                                
                                                  ))
        live_stage_label.grid(row=0, column=0, padx=10)

        # Live follow up label
        live_fu_label = customtkinter.CTkLabel(live_modified_stage_frame,
                                               text='No follow up selected',
                                               font=customtkinter.CTkFont(
                                                   family="Roboto Medium",
                                                   size=20,
                                                   weight="bold"
                                               ))
        live_fu_label.grid(row=1, column=0, padx=10)

        # Live assigned user label
        live_user_label = customtkinter.CTkLabel(live_modified_stage_frame,
                                                 text='No user selected',
                                                 font=customtkinter.CTkFont(
                                                     family="Roboto Medium",
                                                     size=20,
                                                     weight="bold"
                                                ))
        live_user_label.grid(row=2, column=0, padx=10)

        # Add button
        stage_submit_button = customtkinter.CTkButton(add_stage_window,
                                                      text="Add",
                                                      corner_radius=50,
                                                      fg_color="#38753e",
                                                      hover_color="#2c5c31",
                                                      command=add_stage_func,
                                                      font=customtkinter.CTkFont(
                                                          family="Roboto Regular",
                                                          size=15))
        stage_submit_button.grid(row=2, column=0, padx=10, pady=(0, 20))
        
    # Remove a selected pipeline stage condition
    def remove_stage_condition(self, key: int=1) -> None:

        # If selected pipeline has no condition
        if len(self.conditions_dict[key]) == 0:
            no_condition_frame = customtkinter.CTkToplevel()
            no_condition_frame.title(f"{self.user_desgination[key][0]} Pipeline")
            no_condition_frame.attributes("-topmost", True)
            no_condition_frame.geometry("300x120")
            no_condition_frame.resizable(False, False)
            no_condition_frame.pack_propagate(True)
            center_new_window(self, no_condition_frame)
            no_condition_frame_label = customtkinter.CTkLabel(no_condition_frame,
                                                              text="There are no conditions for this pipeline")
            no_condition_frame_label.pack(padx=30, pady=20, fill="x", anchor="center")
            no_condition_button = customtkinter.CTkButton(no_condition_frame,
                                                          text="OK",
                                                          command=no_condition_frame.destroy)
            no_condition_button.pack(pady=(0, 20), anchor="center")

        # If selected pipeline has atleast 1 condition
        elif len(self.conditions_dict[key]) > 0:

            # Function that will update the pipeline condition dictionary
            def remove_selected_condition():
                index = selected_condition.get()
                del self.conditions_dict[key][index]
                no_condition_frame.destroy()
                self.display_assigned_user_followup(key)

            # Pipeline conditions window
            no_condition_frame = customtkinter.CTkToplevel()
            no_condition_frame.title(f"{self.user_desgination[key][0]} Pipeline")
            no_condition_frame.attributes("-topmost", True)
            no_condition_frame.resizable(False, False)
            no_condition_frame.geometry("500x400")
            no_condition_frame.grid_rowconfigure(1, weight=1)
            no_condition_frame.grid_columnconfigure(0, weight=1)
            center_new_window(self, no_condition_frame)

            # Select a condition to remove label
            delete_condition_top_label = customtkinter.CTkLabel(no_condition_frame,
                                                                text="Select a stage condition to remove",
                                                                font=customtkinter.CTkFont(
                                                                    size=18,
                                                                    family="Roboto Medium"
                                                                ))
            delete_condition_top_label.grid(row=0, column=0, padx=10, pady=(20, 0))

            # Scrollable frame that will contain all pipeline conditions
            conditions_scrollable_frame = customtkinter.CTkScrollableFrame(no_condition_frame)
            conditions_scrollable_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
            conditions_scrollable_frame.grid_columnconfigure(1, weight=1)

            # Remove button that will remove the selected pipeline stage condition
            remove_condition_button = customtkinter.CTkButton(no_condition_frame,
                                                              text="Remove Condition",
                                                              fg_color='#c94040',
                                                              hover_color='#8c2626',
                                                              command=remove_selected_condition)
            remove_condition_button.grid(row=2, column=0, padx=20, pady=(5, 10), sticky="ns")

            # Variable that will hold the number of the selected condition to be removed
            selected_condition = customtkinter.IntVar()

            # Iterator for number of stage conditions per pipeline
            row_number = 0

            # Iterate through conditions list of selected pipeline key
            for index, condition in enumerate(self.conditions_dict[key]):

                # Parse condition dictionary
                for stage, value in condition.items():

                    # Create frame that will hold the condition information
                    per_stage_frame = customtkinter.CTkFrame(conditions_scrollable_frame,
                                                                border_width=3,
                                                                corner_radius=25,
                                                                width=400,
                                                                height=200)
                    per_stage_frame.grid(row=row_number, column=1, padx=10, pady=10, sticky="nsew")
                    per_stage_frame.grid_columnconfigure(0, weight=1)

                    # Radio button for a condition
                    stage_select_button = customtkinter.CTkRadioButton(conditions_scrollable_frame,
                                                                    variable=selected_condition,
                                                                    value=index,
                                                                    text=f"Condition {index + 1}")
                    stage_select_button.grid(row=row_number, column=0, padx=(10, 5), pady=10, sticky="e")

                    # Name of the stage condition
                    live_stage_label = customtkinter.CTkLabel(per_stage_frame,
                                                            text=stage,
                                                            anchor="center",
                                                            wraplength=300,
                                                            font=customtkinter.CTkFont(
                                                                family="Roboto Medium",
                                                                size=16,
                                                                weight="normal"
                                                            ))
                    live_stage_label.grid(row=0, column=0, padx=10, pady=5)

                    # Follow up of the stage condition
                    live_fu_label = customtkinter.CTkLabel(per_stage_frame,
                                                        text=value[1],
                                                        anchor="center",
                                                        wraplength=300,
                                                        font=customtkinter.CTkFont(
                                                            family="Roboto Medium",
                                                            size=16,
                                                            weight="normal"
                                                        ))
                    live_fu_label.grid(row=1, column=0, padx=10, pady=5)

                    # Assigned user of the stage condition
                    live_user_label = customtkinter.CTkLabel(per_stage_frame,
                                                            text=value[2],
                                                            anchor="center",
                                                            wraplength=300,
                                                            font=customtkinter.CTkFont(
                                                                family="Roboto Medium",
                                                                size=16,
                                                                weight="normal"
                                                            ))
                    live_user_label.grid(row=2, column=0, padx=10, pady=5)

                    # Increment row number
                    row_number += 1

    # Selection between two run options
    def select_run_option(self) -> None:

        # Pop up window for two run options
        select_run_option_window = customtkinter.CTkToplevel()
        select_run_option_window.geometry("400x200")
        select_run_option_window.title("Run Tool")
        select_run_option_window.attributes("-topmost", True)
        select_run_option_window.resizable(False, False)
        select_run_option_window.grid_columnconfigure(0, weight=1)
        select_run_option_window.grid_rowconfigure(0, weight=1)
        center_new_window(self, select_run_option_window)

        select_run_option_label = customtkinter.CTkLabel(select_run_option_window,
                                                         text="Select a run option")
        select_run_option_label.grid(row=0, column=0, padx=10, pady=10, stick="nsew")

        # Button for Generating New Deals
        run_tool_button = customtkinter.CTkButton(select_run_option_window,
                                                  text='Generate New Deals',
                                                  command=lambda:self.run_tool(select_run_option_window))
        run_tool_button.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        # Button for Grabbing Deal ID of all New Deals
        grab_new_deals_button = customtkinter.CTkButton(select_run_option_window,
                                                        text="Grab New Deals Deal ID",
                                                        command=lambda: self.grab_new_deals(select_run_option_window))
        grab_new_deals_button.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

    # Function that will run backend code of Generating New Deals
    def run_tool(self, window: customtkinter.CTkFrame) -> None:

        window.destroy()

        # Pass true to display Run Tool Button in all pipeline display
        self.display_all_pipeline_conditions(True)

    # Function that will pop up confirmation of Grabbing Deal ID of all New Deals
    def grab_new_deals(self, window: customtkinter.CTkFrame) -> None:

        # Pop up confirmation window for running run option
        window.destroy()
        grab_new_deals_window = customtkinter.CTkToplevel()
        grab_new_deals_window.geometry("400x150")
        grab_new_deals_window.title("Grab New Deals")
        grab_new_deals_window.attributes("-topmost", True)
        grab_new_deals_window.resizable(False, False)
        grab_new_deals_window.grid_columnconfigure(0, weight=1)
        grab_new_deals_window.grid_rowconfigure(0, weight=1)
        center_new_window(self, grab_new_deals_window)

        grab_new_deals_label = customtkinter.CTkLabel(grab_new_deals_window,
                                                      text="This will grab Deal IDs of all New Deals, run tool?")
        grab_new_deals_label.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Confirm button for running tool option
        confirm_button = customtkinter.CTkButton(grab_new_deals_window,
                                                 text="Confirm",
                                                 command=lambda: self.confirm_grab_new_deals(grab_new_deals_window))
        confirm_button.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

    # Tool running in background window
    def confirm_grab_new_deals(self, window: customtkinter.CTkFrame) -> None:


        window.destroy()

        # Pop up new window
        self.grab_new_deals_window = customtkinter.CTkToplevel()
        self.grab_new_deals_window.geometry("400x150")
        self.grab_new_deals_window.title("Grab New Deals")
        self.grab_new_deals_window.attributes("-topmost", True)
        self.grab_new_deals_window.resizable(False, False)
        self.grab_new_deals_window.grid_columnconfigure(0, weight=1)
        self.grab_new_deals_window.grid_rowconfigure(0, weight=1)
        center_new_window(self, self.grab_new_deals_window)

        grab_new_deals_label = customtkinter.CTkLabel(self.grab_new_deals_window,
                                                     text="Tool is running in background.\nPlease wait for the tool to finish",
                                                     font=customtkinter.CTkFont(
                                                         family="Roboto Regular",
                                                         size=16
                                                     ))
        grab_new_deals_label.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Invoke tool backend function after 1 second
        # self.grab_new_deals_window.after(1000, self.run_grab_new_deals)
        threading.Thread(target=self.run_grab_new_deals).start()


    # Function that will run tool backend code in background
    def run_grab_new_deals(self) -> None:

        error_code = grab_new_deals_id()
        if error_code:
            self.wrong_db_credentials(error_code)

        else:

            # Pop up confirmation window after successfully running tool option
            confirmation_window = customtkinter.CTkToplevel(self)
            confirmation_window.pack_propagate(True)
            center_new_window(self, confirmation_window)
            confirmation_window.title("Grab New Deals")
            confirmation_window.geometry("300x150")
            label = customtkinter.CTkLabel(confirmation_window, text=f"Succesfully Grabbed New Deals Deal ID")
            label.pack(pady=20, padx=20, fill="y", expand=True)
            button = customtkinter.CTkButton(confirmation_window, text="OK", command=confirmation_window.destroy)
            button.pack(pady=20, padx=20)   

            self.grab_new_deals_window.destroy()

    # Display assigned values for pipeline and conditions of pipeline
    def display_assigned_user_followup(self, key: int=1) -> None:

        # Pipeline-Conditions frame
        pipeline_conditions_frame = customtkinter.CTkFrame(self.conditions_frame,
                                                           border_width=2)
        pipeline_conditions_frame_label = customtkinter.CTkLabel(pipeline_conditions_frame,
                                                                 text=f"{self.user_desgination[key][0]} Pipeline",
                                                                 font=customtkinter.CTkFont(
                                                                     family="Roboto Black",
                                                                     size=35))
        pipeline_conditions_frame_label.grid(row=0, column=0, padx=5, pady=(20, 5), sticky="nsew")
        pipeline_conditions_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        pipeline_conditions_frame.grid_columnconfigure(0, weight=1)
        pipeline_conditions_frame.grid_rowconfigure((0,1,2,4), weight=0)
        pipeline_conditions_frame.grid_rowconfigure(3, weight=3)

        # Conditions scrollable frame
        conditions_frame = customtkinter.CTkScrollableFrame(pipeline_conditions_frame,
                                                            label_text="Stage Conditions",
                                                            label_font=customtkinter.CTkFont(
                                                                         family='Roboto Black',
                                                                         size=25))
        conditions_frame.grid(row=3, column=0, padx=5, pady=5, sticky="nsew")

        # Pipeline Buttons Frame
        pipeline_buttons_frame = customtkinter.CTkFrame(pipeline_conditions_frame,
                                                        fg_color="transparent")
        pipeline_buttons_frame.grid(row=4, column=0, padx=5, pady=5, sticky="nsew")
        pipeline_buttons_frame.grid_rowconfigure(0, weight=1)
        pipeline_buttons_frame.grid_columnconfigure((0,1,2), weight=1)

        # Edit pipeline button
        edit_pipeline_values_button = customtkinter.CTkButton(pipeline_buttons_frame,
                                                              text="Edit Pipeline",
                                                              fg_color="#4682b4",
                                                              hover_color="#325d81",
                                                              command= lambda pipeline_key=key: self.edit_pipeline_data(pipeline_key),
                                                              font=customtkinter.CTkFont(
                                                                  family="Roboto Medium"))
        edit_pipeline_values_button.grid(row=0, column=0, padx=10, pady=5)

        # Add condition button
        add_stage_condition_button = customtkinter.CTkButton(pipeline_buttons_frame,
                                                             text="Add Stage Condition",
                                                             fg_color="#4682b4",
                                                             hover_color="#325d81",
                                                             command= lambda pipeline_key=key: self.add_stage_condition(pipeline_key),
                                                             font=customtkinter.CTkFont(
                                                                  family="Roboto Medium"))
        add_stage_condition_button.grid(row=0, column=1, padx=10, pady=5)

        # Remove condition button
        remove_stage_condition_button = customtkinter.CTkButton(pipeline_buttons_frame,
                                                                text="Remove Stage Condition",
                                                                fg_color="#4682b4",
                                                                hover_color="#325d81",
                                                                command= lambda pipeline_key=key: self.remove_stage_condition(pipeline_key),
                                                                font=customtkinter.CTkFont(
                                                                  family="Roboto Medium"))
        remove_stage_condition_button.grid(row=0, column=2, padx=10, pady=5)

        # Pipeline follow up label
        pipeline_follow_up_label = customtkinter.CTkLabel(pipeline_conditions_frame,
                                                          text=f"{self.user_desgination[key][1]}",
                                                          anchor="center",
                                                          font=customtkinter.CTkFont(
                                                              family='Roboto Medium',
                                                              size=18))
        pipeline_follow_up_label.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        # Pipeline assigned user label
        pipeline_user_label = customtkinter.CTkLabel(pipeline_conditions_frame,
                                                     text=f"{self.user_desgination[key][2]}",
                                                     anchor="center",
                                                     font=customtkinter.CTkFont(
                                                         family='Roboto Medium',
                                                         size=18))
        pipeline_user_label.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")


        # Condition labels
        if len(self.conditions_dict[key]) == 0:

            # If there are no stage conditions for the selected pipeline
            no_conditions_label = customtkinter.CTkLabel(conditions_frame,
                                                         text="There are no Stage Conditions for this pipeline",
                                                         anchor="center",
                                                         font=customtkinter.CTkFont(
                                                             family='Roboto Medium',
                                                             size=15))
            no_conditions_label.pack(padx=10, pady=5)

        # If there is atleast 1 condition for the selected pipeline
        elif len(self.conditions_dict[key]) > 0:

            # Iterate through conditions list from the selected pipeline
            for condition in self.conditions_dict[key]:

                # Parse conditions dictionary
                for stage, value in condition.items():

                    # Per condition frame
                    per_stage_frame = customtkinter.CTkFrame(conditions_frame,
                                                                border_width=4,
                                                                corner_radius=25)
                    per_stage_frame.pack(padx=10, pady=5, fill="x", anchor="center")
                    per_stage_frame.grid_columnconfigure(0, weight=1)

                    # Stage name label
                    live_stage_label = customtkinter.CTkLabel(per_stage_frame,
                                                            text=stage,
                                                            font=customtkinter.CTkFont(
                                                                family="Roboto Medium",
                                                                size=18,
                                                                weight="bold"
                                                            ))
                    live_stage_label.grid(row=0, column=0, padx=10, pady=5)

                    # Stage follow up label
                    live_fu_label = customtkinter.CTkLabel(per_stage_frame,
                                                        text=value[1],
                                                        font=customtkinter.CTkFont(
                                                            family="Roboto Medium",
                                                            size=18,
                                                            weight="bold"
                                                        ))
                    live_fu_label.grid(row=1, column=0, padx=10, pady=5)

                    # Stage assigned user label
                    live_user_label = customtkinter.CTkLabel(per_stage_frame,
                                                            text=value[2],
                                                            font=customtkinter.CTkFont(
                                                                family="Roboto Medium",
                                                                size=18,
                                                                weight="bold"
                                                            ))
                    live_user_label.grid(row=2, column=0, padx=10, pady=5)

    # Remove ANI Duplicates and separate the duplicated ANI number in another excel file
    def remove_rc_duplicates(self) -> None:
        
        # Function will run the backend code for removing ANI Duplicates
        def confirmed_save() -> None:

            confirm_save_data_window.destroy()

            # Run backend code
            remove_rc_duplicates()

            # Display confirmation window of removing ani duplicates
            save_confirmation_window = customtkinter.CTkToplevel(self)
            center_new_window(self, save_confirmation_window)
            save_confirmation_window.pack_propagate(True)
            save_confirmation_window.attributes('-topmost', True)
            save_confirmation_window.title('Remove JC Duplicates')
            save_confirmation_window_label = customtkinter.CTkLabel(save_confirmation_window,
                                                                    text="ANI duplicates has been successfully removed")
            save_confirmation_window_label.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
            save_confirmation_window_button = customtkinter.CTkButton(save_confirmation_window,
                                                                    text="OK",
                                                                    command=save_confirmation_window.destroy)
            save_confirmation_window_button.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")

        # Display remove ani duplicates window
        confirm_save_data_window = customtkinter.CTkToplevel()
        confirm_save_data_window.title("Remove JC Duplicates")
        confirm_save_data_window.attributes("-topmost", True)
        confirm_save_data_window.geometry("400x150")
        confirm_save_data_window.grid_rowconfigure((0,1), weight=1)
        confirm_save_data_window.grid_columnconfigure(0, weight=1)
        center_new_window(self, confirm_save_data_window)
        confirm_save_data_window_label = customtkinter.CTkLabel(confirm_save_data_window,
                                                                text="This will remove all ANI duplicates from input files, are you sure?")
        confirm_save_data_window_label.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        confirm_button_frame = customtkinter.CTkFrame(confirm_save_data_window, fg_color="transparent")
        confirm_button_frame.grid(row=1, column=0, padx=10, pady=(0,5), stick="nsew")
        confirm_button_frame.grid_columnconfigure((0,1), weight=1)
        confirm_button_frame.grid_rowconfigure(0, weight=1)

        # Add confirmation and cancel button for removing ani duplicates
        confirm_button = customtkinter.CTkButton(confirm_button_frame,
                                                 text="Confirm",
                                                 command=confirmed_save)
        confirm_button.grid(row=0, column=0, padx=10, pady=5)
        cancel_button = customtkinter.CTkButton(confirm_button_frame,
                                                text="Cancel",
                                                command=confirm_save_data_window.destroy)
        cancel_button.grid(row=0, column=1, padx=10, pady=5)



    """"""""""""""""""""""""
    #    HELPER METHODS    #
    """"""""""""""""""""""""

    def read_conditions_designations(self) -> 'tuple[dict[int: list], dict[int: list]]':

        # Define path of user designatio and condition JSON Data
        conditions_path = 'data/conditions_input/conditions_dict.json'
        user_designation_path = 'data/conditions_input/user_designation.json'

        # Read user desgination JSON data
        with open(user_designation_path, 'r', encoding='utf-8') as designations_json_file:
            user_designation_raw = json.load(designations_json_file)

        # Read conditions JSON data
        with open(conditions_path, 'r', encoding='utf-8') as conditions_json_file:
            condition_dict_raw = json.load(conditions_json_file)

        # Convert key to int data type
        user_designation = {int(key): value for key, value in user_designation_raw.items()}
        condition_dict = {int(key): value for key, value in condition_dict_raw.items()}

        return user_designation, condition_dict
    
    def center_main_window(self, width: int, height: int) -> str:
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 1.5))
        return f"{width}x{height}+{x}+{y}"

    def extract_pipedrive_stages(self) -> dict:

        # Define path and read columns of pipedrive data
        pipedrive_path = 'data/pipedrive'
        pipedrive_data_list = os.listdir(pipedrive_path)
        pipedrive_df = pd.read_csv(f"{pipedrive_path}/{pipedrive_data_list[0]}",
                                     usecols=['Deal - Stage', 'Deal - Pipeline'])
        pipedrive_df['Pipeline'] = pipedrive_df['Deal - Pipeline'].str.split('Pipeline').str[0].str.strip()

        # Group by pipeline name and create a list of unique stages per pipeline
        stages_per_pipeline_df = pipedrive_df.groupby('Pipeline')['Deal - Stage'].agg(
            lambda x: sorted(list(x.unique()))).reset_index()
        pipeline_stages_dict = stages_per_pipeline_df.set_index('Pipeline')['Deal - Stage'].to_dict()

        # Add stage Accepted Offer - Junior if not present in stages of Junior Sales Team Pipeline
        if "Accepted Offer - Junior Sales" not in pipeline_stages_dict['Junior Sales Team']:
            pipeline_stages_dict['Junior Sales Team'].append("Accepted Offer - Junior Sales")
        pipeline_stages_dict['Junior Sales Team'].sort()

        return pipeline_stages_dict

    def confirm_run_tool(self, window: customtkinter.CTkFrame) -> None:
        
        # Close parent window
        window.destroy()

        # Pop up window notifying tool is running in background
        self.tool_run_window = customtkinter.CTkToplevel()
        center_new_window(self, self.tool_run_window)
        # self.tool_run_window.attributes("-topmost", True)
        self.tool_run_window.resizable(False, False)
        self.tool_run_window.geometry("400x200")
        self.tool_run_window.grid_columnconfigure(0, weight=1)
        self.tool_run_window.grid_rowconfigure(0, weight=1)
        self.tool_run_window.title("Generate New Deals")

        self.tool_run_label = customtkinter.CTkLabel(self.tool_run_window,
                                                     text="Tool is running in background.\nPlease wait for the tool to finish",
                                                     font=customtkinter.CTkFont(
                                                         family="Roboto Regular",
                                                         size=16
                                                     ))
        self.tool_run_label.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.tool_run_window.after(1000, self.trigger_tool)

    def done_tool_run(self) -> None:

        # Pop up new window that notifies tool is done running
        confirmation_window = customtkinter.CTkToplevel(self)
        confirmation_window.pack_propagate(True)
        confirmation_window.attributes('-topmost', True)
        center_new_window(self, confirmation_window)
        confirmation_window.title("Generate New Deals")
        confirmation_window.geometry("300x150")
        label = customtkinter.CTkLabel(confirmation_window, text=f"Succesfully Generated New Deals")
        label.pack(pady=20, padx=20, fill="y", expand=True)
        button = customtkinter.CTkButton(confirmation_window, text="OK", command=confirmation_window.destroy)
        button.pack(pady=20, padx=20)

        # Close parent window
        self.tool_run_window.destroy()

    def wrong_db_credentials(self, error_code) -> None:

        # error_string_label = ""

        # # Filter for error code
        # if error_code == 'db_wrong':
        #     error_string_label = "Incorrect database credentials.\nPlease check the database config file"
        #     self.tool_run_window.destroy()
        # elif 'rc_empty' in error_code:
        #     error_string_label = "Run Tool failed.\nNo JC file is present in the JC Folder"
        if 'main' in error_code:
            self.tool_run_window.destroy()
        else:
            self.grab_new_deals_window.destroy()

        # Pop up window that notifies wrong database credentials
        confirmation_window = customtkinter.CTkToplevel(self)
        confirmation_window.pack_propagate(True)
        confirmation_window.attributes('-topmost', True)
        center_new_window(self, confirmation_window)
        confirmation_window.title("Failed Tool Run")
        confirmation_window.geometry("300x150")
        label = customtkinter.CTkLabel(confirmation_window, text="Tool Run Failed")
        label.pack(pady=20, padx=20, fill="y", expand=True)
        button = customtkinter.CTkButton(confirmation_window, text="OK", command=confirmation_window.destroy)
        button.pack(pady=20, padx=20)

    def trigger_tool(self) -> None:

        # Define user designation and conditions JSON path
        conditions_path = 'data/conditions_input/conditions_dict.json'
        user_designation_path = 'data/conditions_input/user_designation.json'

        # Save conditions JSON Data
        with open(conditions_path, 'w', encoding='utf-8') as conditions_json_file:
            json.dump(self.conditions_dict, conditions_json_file)

        # Save user designation JSON Data
        with open(user_designation_path, 'w', encoding='utf-8') as designations_json_file:
            json.dump(self.user_desgination, designations_json_file)

        # Get return of backend run
        # run_error_check = run_tool()

        # If wrong credentials, pop up warning
        try:
            threading.Thread(target=self.run_clean_up_with_callback, args=(run_tool,)).start()
        except Exception as e:
            self.wrong_db_credentials('main')
        # if run_error_check != 'pass':
        #     self.wrong_db_credentials(run_error_check)

        # # If credentials is correct, run code
        # else:
        #     self.done_tool_run()
    
    def run_clean_up_with_callback(self, func):
        try:
            error_check =  func()
            if error_check == 'pass':
                self.done_tool_run()
            else:
                self.wrong_db_credentials('main')

        except:
            self.wrong_db_credentials('main')

def main() -> None:

    # Create instance of a class and start loop
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
