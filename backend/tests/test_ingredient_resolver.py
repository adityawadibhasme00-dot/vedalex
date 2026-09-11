from app.services.ingredient_resolver import IngredientResolverService

def test_canonical_botanical_resolution():
    # Test Devanagari Hindi
    res_hi = IngredientResolverService.resolve("अश्वगंधा")
    assert res_hi is not None
    assert res_hi.canonical_id == "ING-ASHWAGANDHA"
    assert res_hi.accepted_botanical_name == "Withania somnifera (L.) Dunal"
    assert res_hi.api_monograph_id == "API-VOL1-008"

    # Test Marathi vernacular
    res_mr = IngredientResolverService.resolve("आस्कंद")
    assert res_mr is not None
    assert res_mr.canonical_id == "ING-ASHWAGANDHA"

    # Test Tamil vernacular
    res_ta = IngredientResolverService.resolve("அமுக்கரா")
    assert res_ta is not None
    assert res_ta.canonical_id == "ING-ASHWAGANDHA"

    # Test Brahmi
    res_brahmi = IngredientResolverService.resolve("ब्राह्मी")
    assert res_brahmi is not None
    assert res_brahmi.canonical_id == "ING-BRAHMI"
    assert res_brahmi.accepted_botanical_name == "Bacopa monnieri (L.) Wettst."
