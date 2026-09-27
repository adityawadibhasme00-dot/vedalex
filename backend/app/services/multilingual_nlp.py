import json
import os
import re


class MultilingualNLPEngine:
    """
    Multilingual NLP engine supporting Indic language intake, code-switching detection,
    glossary entity normalization, and meaning preservation verification across 10 languages:
    English, Hindi (हिन्दी), Marathi (मराठी), Tamil (தமிழ்), Telugu (తెలుగు),
    Kannada (ಕನ್ನಡ), Bengali (বাংলা), Gujarati (ગુજરાતી), Malayalam (മലയാളം), Sanskrit (संस्कृत).
    """
    _synonyms_data: dict[str, dict] = {}

    @classmethod
    def load_synonyms(cls):
        if not cls._synonyms_data:
            synonyms_path = os.path.join(os.path.dirname(__file__), "..", "knowledge", "botanical_synonyms.json")
            if os.path.exists(synonyms_path):
                with open(synonyms_path, encoding="utf-8") as f:
                    cls._synonyms_data = json.load(f)

    # Distinctive Indic spellings used to disambiguate shared Devanagari scripts.
    _MARATHI_HINTS = ["हळद", "तुळस", "कडूनिंब", "लिंब", "आस्कंद", "डोरगुंज", "शंखावली"]
    _HINDI_HINTS = ["हल्दी", "तुलसी", "नीम", "गुग्गुल", "असगन्ध", "शंखपुष्पी", "सर्पगंधा", "हरिद्रा"]
    _SANSKRIT_HINTS = ["निम्ब", "गुग्गुलु", "शतमूली", "हयगन्धा", "भीरु"]
    _MARATHI_MARKERS = ["आहे", "करतो", "साठी", "मध्ये", "झाले", "औषध", "झोप", "सुधारते"]

    @classmethod
    def detect_language(cls, text: str) -> str:
        """
        Detects primary script / language. Returns 'mr', 'hi', 'sa', 'ta', 'te', 'kn', 'bn', 'gu', 'ml', or 'en'.
        """
        devanagari_chars = len(re.findall(r'[\u0900-\u097F]', text))
        tamil_chars = len(re.findall(r'[\u0B80-\u0BFF]', text))
        telugu_chars = len(re.findall(r'[\u0C00-\u0C7F]', text))
        kannada_chars = len(re.findall(r'[\u0C80-\u0CFF]', text))
        bengali_chars = len(re.findall(r'[\u0980-\u09FF]', text))
        gujarati_chars = len(re.findall(r'[\u0A80-\u0AFF]', text))
        malayalam_chars = len(re.findall(r'[\u0D00-\u0D7F]', text))

        if devanagari_chars > 0:
            lower = text.lower()
            if any(hint in lower for hint in cls._MARATHI_HINTS):
                return "mr"
            if any(hint in lower for hint in cls._HINDI_HINTS):
                return "hi"
            if any(hint in lower for hint in cls._SANSKRIT_HINTS):
                return "sa"
            if any(marker in lower for marker in cls._MARATHI_MARKERS):
                return "mr"
            return "hi"
        elif tamil_chars > 0:
            return "ta"
        elif telugu_chars > 0:
            return "te"
        elif kannada_chars > 0:
            return "kn"
        elif bengali_chars > 0:
            return "bn"
        elif gujarati_chars > 0:
            return "gu"
        elif malayalam_chars > 0:
            return "ml"
        return "en"

    @classmethod
    def normalize_botanical_mentions(cls, text: str) -> list[tuple[str, str, float]]:
        """
        Extracts and normalizes botanical mentions from text in any supported script.
        Returns List of (raw_token, canonical_id, confidence) where raw_token is the
        actual substring matched inside the user's input text.
        """
        cls.load_synonyms()
        results = []
        lower_text = text.lower()

        for canonical_id, data in cls._synonyms_data.items():
            matched = False
            for _lang, aliases in data.items():
                if isinstance(aliases, list):
                    for alias in aliases:
                        if not alias:
                            continue
                        m = re.search(re.escape(alias.lower()), lower_text)
                        if m:
                            span = m.start()
                            raw_token = text[span:span + len(alias)]
                            results.append((raw_token, canonical_id, 0.95))
                            matched = True
                            break
                if matched:
                    break

        results.sort(key=lambda r: lower_text.find(r[0].lower()) if r[0].lower() in lower_text else 0)
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
