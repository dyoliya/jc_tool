import os
import json
import pandas as pd


def _safe_str(x) -> str:
    """Convert to clean string (handles NaN)."""
    if pd.isna(x):
        return ""
    return str(x).strip()


def _follow_up(team_responsible: str) -> str:
    """
    Rule:
    {"Team Responsible"} + " - Abandoned Call Follow Up"
    """
    team_responsible = _safe_str(team_responsible)
    return f"{team_responsible} - Abandoned Call Follow Up" if team_responsible else " - Abandoned Call Follow Up"


def update_pipeline_json_from_xlsx(
    xlsx_path: str = os.path.join("data", "conditions_input", "Pipedrive Stages - Stages.xlsx"),
    out_dir: str = os.path.join("data", "conditions_input"),
) -> tuple[dict, dict]:
    """
    Reads the XLSX and writes/overwrites:
      - user_designation.json
      - conditions_dict.json

    Returns: (user_designation_dict, conditions_dict)
    """

    if not os.path.exists(xlsx_path):
        raise FileNotFoundError(f"XLSX not found: {xlsx_path}")

    os.makedirs(out_dir, exist_ok=True)

    # Read sheet (uses first sheet by default)
    df = pd.read_excel(xlsx_path)

    required_cols = [
        "JSONKey",
        "Pipeline (Clean)",
        "Team Responsible",
        "PD Follow Up Tagging",
        "Stage",
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required column(s) in XLSX: {missing}")

    # Normalize columns
    df["JSONKey"] = df["JSONKey"].apply(_safe_str)
    df["Pipeline (Clean)"] = df["Pipeline (Clean)"].apply(_safe_str)
    df["Team Responsible"] = df["Team Responsible"].apply(_safe_str)
    df["PD Follow Up Tagging"] = df["PD Follow Up Tagging"].apply(_safe_str)
    df["Stage"] = df["Stage"].apply(_safe_str)

    # Drop rows with no JSONKey (can’t map them)
    df = df[df["JSONKey"] != ""].copy()

    # -------------------------
    # Build user_designation.json
    # -------------------------
    # Only take first instance per JSONKey
    first_per_key = df.drop_duplicates(subset=["JSONKey"], keep="first")

    user_designation: dict[str, list[str]] = {}
    for _, row in first_per_key.iterrows():
        key = row["JSONKey"]  # keep as string in JSON

        pipeline_name = row["Pipeline (Clean)"]
        fu = _follow_up(row["Team Responsible"])
        tagging_user = row["PD Follow Up Tagging"]

        # You can choose to skip if pipeline_name is blank
        if pipeline_name == "":
            continue

        user_designation[key] = [pipeline_name, fu, tagging_user]

    # -------------------------
    # Build conditions_dict.json
    # -------------------------
    conditions_dict: dict[str, list[dict]] = {}

    # Group by JSONKey; each row becomes {Stage: ["Deal - Stage", fu, tagging]}
    for key, group in df.groupby("JSONKey", sort=False):
        conditions: list[dict] = []

        for _, row in group.iterrows():
            stage_name = row["Stage"]
            if stage_name == "":
                continue

            fu = _follow_up(row["Team Responsible"])
            tagging_user = row["PD Follow Up Tagging"]

            conditions.append(
                {stage_name: ["Deal - Stage", fu, tagging_user]}
            )

        # Ensure key exists even if it ends up empty (optional)
        conditions_dict[key] = conditions

    # -------------------------
    # Write JSON files (overwrite / create)
    # -------------------------
    user_designation_path = os.path.join(out_dir, "user_designation.json")
    conditions_path = os.path.join(out_dir, "conditions_dict.json")

    with open(user_designation_path, "w", encoding="utf-8") as f:
        json.dump(user_designation, f, indent=4, ensure_ascii=False)

    with open(conditions_path, "w", encoding="utf-8") as f:
        json.dump(conditions_dict, f, indent=4, ensure_ascii=False)

    return user_designation, conditions_dict


if __name__ == "__main__":
    update_pipeline_json_from_xlsx()
    print("✅ Updated user_designation.json and conditions_dict.json from XLSX.")
