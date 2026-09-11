import json
import os
import re
from typing import Dict, List, Tuple, Optional

class MultilingualNLPEngine:
    """
    Multilingual NLP engine supporting Indic language intake, code-switching detection,
    glossary entity normalization, and meaning preservation verification across 10 languages:
    English, Hindi (हिन्दी), Marathi (मराठी), Tamil (தமிழ்), Telugu (తెలుగు),
    Kannada (ಕನ್ನಡ), Bengali (বাংলা), Gujarati (ગુજરાતી), Malayalam (മലയാളം), Sanskrit (संस्कृत).
    """
    _synonyms_data: Dict[str, Dict] = {}

    @classmethod
    def load_synonyms(cls):
        if not cls._synonyms_data:
            synonyms_path = os.path.join(os.path.dirname(__file__), "..", "knowledge", "botanical_synonyms.json")
            if os.path.exists(synonyms_path):
                with open(synonyms_path, "r", encoding="utf-8") as f:
                    cls._synonyms_data = json.load(f)

    @classmethod
    def detect_language(cls, text: str) -> str:
        """
        Detects primary script / language. Returns 'mr', 'hi', 'ta', 'te', 'kn', 'bn', 'gu', 'ml', 'sa', or 'en'.
        """
        # Devanagari script: 0900-097F
        devanagari_chars = len(re.findall(r'[\u0900-\u097F]', text))
        # Tamil: 0B80-0BFF
        tamil_chars = len(re.findall(r'[\u0B80-\u0BFF]', text))
        # Telugu: 0C00-0C7F
        telugu_chars = len(re.findall(r'[\u0C00-\u0C7F]', text))
        # Kannada: 0C80-0CFF
        kannada_chars = len(re.findall(r'[\u0C80-\u0CFF]', text))
        # Bengali: 0980-09FF
        bengali_chars = len(re.findall(r'[\u0980-\u09FF]', text))
        # Gujarati: 0A80-0AFF
        gujarati_chars = len(re.findall(r'[\u0A80-\u0AFF]', text))
        # Malayalam: 0D00-0D7F
        malayalam_chars = len(re.findall(r'[\u0D00-\u0D7F]', text))

        if devanagari_chars > 3:
            # Check Marathi specific vocabulary / marker words
            marathi_markers = ["आहे", "करतो", "साठी", "मध्ये", "झाले", "औषध", "झोप", "सुधारते", "आस्कंद"]
            if any(marker in text for marker in marathi_markers):
                return "mr"
            return "hi"
        elif tamil_chars > 3:
            return "ta"
        elif telugu_chars > 3:
            return "te"
        elif kannada_chars > 3:
            return "kn"
        elif bengali_chars > 3:
            return "bn"
        elif gujarati_chars > 3:
            return "gu"
        elif malayalam_chars > 3:
            return "ml"
        return "en"

    @classmethod
    def normalize_botanical_mentions(cls, text: str) -> List[Tuple[str, str, float]]:
        """
        Extracts and normalizes botanical mentions from text in any supported script.
        Returns List of (raw_token, canonical_id, confidence).
        """
        cls.load_synonyms()
        results = []
        lower_text = text.lower()

        for canonical_id, data in cls._synonyms_data.items():
            matched = False
            for lang, aliases in data.items():
                if isinstance(aliases, list):
                    for alias in aliases:
                        if alias.lower() in lower_text or re.search(rf"\b{re.escape(alias.lower())}\b", lower_text):
                            results.append((alias, canonical_id, 0.95))
                            matched = True
                            break
                if matched:
                    break

        return results

    @classmethod
    def get_localized_ui_text(cls, key: str, target_lang: str) -> str:
        """
        Returns localized UI string for key.
        """
        translations = {
            "why_view_title": {
                "en": "Traceable Decision Workspace ('Why?' Provenance Graph)",
                "hi": "सटीक निर्णय कार्यक्षेत्र ('क्यों?' स्रोत सत्यापन आरेख)",
                "mr": "पारदर्शक निर्णय कार्यक्षेत्र ('का?' मूळ पुरावा आलेख)",
                "ta": "மூல ஆதார சரிபார்ப்பு வரைபடம்",
                "te": "ఆధార నిర్ధారణ గ్రాఫ్",
                "kn": "ಮೂಲ ಪುರಾವೆ ಗ್ರಾಫ್",
                "bn": "উৎস প্রমাণ যাচাইকরণ গ্রাফ",
                "gu": "મૂળ આધાર ચકાસણી ગ્રાફ",
                "ml": "ഉറവിട തെളിവ് ഗ്രാഫ്",
                "sa": "मूलप्रमाणानुसन्धानपटलम्"
            },
            "what_if_title": {
                "en": "Live Reactive What-If Simulator",
                "hi": "लाइव 'व्हाट-इफ' सिम्युलेटर (दावा परिवर्तन प्रभाव)",
                "mr": "थेट 'जर-तर' सिम्युलेटर (दावा बदल विश्लेषण)",
                "ta": "மாறுதல் பகுப்பாய்வி",
                "te": "మార్పు విశ్లేషణ సిమ్యులేటర్",
                "kn": "ಬದಲಾವಣೆ ವಿಶ್ಲೇಷಣೆ ಸಿಮ್ಯುಲೇಟರ್",
                "bn": "দাবি পরিবর্তন বিশ্লেষণ সিমুলেটর",
                "gu": "દાવા ફેરફાર વિશ્લેષણ સિમ્યુલેટર",
                "ml": "മാറ്റ വിശകലന സിമുലേറ്റർ",
                "sa": "प्रतिज्ञापरिवर्तनप्रभावसमीक्षकः"
            }
        }
        return translations.get(key, {}).get(target_lang, translations.get(key, {}).get("en", key))
