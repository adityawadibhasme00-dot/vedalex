from typing import Dict, List, Any
from app.models.canonical import CanonicalIngredient

class IngredientLegalityChecker:
    """
    Per-ingredient legality cross-checker (Section 7.2.2).
    Evaluates individual botanicals against:
    1. US FDA Old Dietary Ingredient (ODI) vs New Dietary Ingredient (NDI) List
    2. Health Canada Natural Health Products Ingredients Database (NHPID) Monograph status
    3. FSSAI Ayurveda Aahara Schedule I Permitted Positive List
    """
    @staticmethod
    def check_jurisdiction_legality(
        canonical_ingredients: List[CanonicalIngredient],
        jurisdiction: str
    ) -> Dict[str, Any]:
        results = []
        all_permitted = True

        for ing in canonical_ingredients:
            status = "PERMITTED"
            note = ""
            
            if jurisdiction.lower() in ["india", "in"]:
                if ing.fssai_aahara_status == "permitted":
                    status = "PERMITTED (Schedule I Positive List)"
                    note = f"Listed in API Monograph {ing.api_monograph_id}"
                else:
                    status = "RESTRICTED"
                    all_permitted = False
                    note = "Not found in FSSAI Ayurveda Aahara Schedule I positive list"

            elif jurisdiction.lower() in ["united states", "usa", "us"]:
                if ing.us_fda_ndi_status == "old_dietary_ingredient":
                    status = "PERMITTED (Pre-1994 Old Dietary Ingredient)"
                    note = "Grandfathered under DSHEA 21 U.S.C. 343; no NDI notification required."
                elif ing.us_fda_ndi_status == "ndi_notification_required":
                    status = "NDI NOTIFICATION REQUIRED (75-Day Pre-market Filing)"
                    all_permitted = False
                    note = "Must submit safety dossier under 21 CFR 190.6 75 days prior to marketing."
                else:
                    status = "RESTRICTED / UNLISTED"
                    all_permitted = False

            elif jurisdiction.lower() in ["canada", "ca"]:
                if ing.canada_nhpid_status == "monographed":
                    status = "PERMITTED (NHPID Monograph List)"
                    note = "Eligible for expedited Class I Natural Product Number (NPN) licensing."
                else:
                    status = "CLASS III EVIDENCE REQUIRED"
                    all_permitted = False
                    note = "Requires full safety and efficacy clinical literature package."

            results.append({
                "canonical_id": ing.canonical_id,
                "botanical_name": ing.accepted_botanical_name,
                "status": status,
                "note": note
            })

        return {
            "jurisdiction": jurisdiction,
            "overall_legality_passed": all_permitted,
            "ingredient_checks": results
        }
