"""
Seed data for M5 Cultural Intelligence: Curated traditions and ritual items.
Fulfills the exact 8 traditions per UTSAV spec:
Maharashtrian, Punjabi, Bengali, Tamil, Gujarati, Muslim Nikah, Christian, Telugu.
Each explicitly marked is_verified: True/False with verification_source.
"""

from typing import List, Dict, Any
from backend.app.db.session import SessionLocal
from backend.app.models.models import Tradition, RitualItem

CURATED_TRADITIONS: List[Dict[str, Any]] = [
    {
        "code": "maharashtrian_vedic",
        "regional_name": "Maharashtrian Vedic Lagna",
        "description": "Traditional Maharashtrian Hindu wedding following Ashvalayana/Baudhayana Grhya Sutras.",
        "cultural_notes": "Key customs include Sakhar Puda, Kelvan, Antarpat separation, Mundavalya adornment, and Saptapadi.",
        "is_verified": True,
        "verification_source": "Maharashtra Purohit Parishad Manual & Vedic Grhya Sutra",
        "items": [
            ("Mundavalya (Forehead Ornaments)", "मुंडावळ्या", "2 pairs (Pearl/Bead strings)", "bridal_adornment", "Worn across bride and groom forehead to ward off negative gaze and signify readiness for vivah", "Vivah Muhurat"),
            ("Antarpat (Separation Cloth)", "अंतरपाट", "1 silk cloth with Swastika print", "ceremonial_fabrics", "Held between bride and groom until the Mangalashtaka shlokas culminate at exact Muhurat", "Mangalashtaka"),
            ("Akshata (Sacred Rice)", "अक्षता", "2.5 kg unbroken rice dyed in turmeric", "puja_samagri", "Shower of divine blessings by elders during recitation of sacred verses", "Mangalashtaka"),
            ("Mangalsutra (Black Bead Sacred Thread)", "मंगळसूत्र", "1 piece (two hollow gold vatis)", "sacred_ornaments", "Tied around bride's neck representing lifelong marital sanctity and harmony", "Kanyadaan"),
            ("Supari (Betel Nuts)", "सुपारी", "51 whole unbroken nuts", "offerings", "Invoked as representatives of Ganesha and celestial deities during Avahana", "Gauri Har Pooja"),
            ("Nagvel Pan (Betel Leaves)", "नागवेलीची पाने", "108 fresh leaves", "offerings", "Symbol of life, fertility, and auspicious welcome for all deities", "Gauri Har Pooja"),
            ("Halad Roots (Raw Turmeric)", "हळकुंडे", "250 grams whole roots", "puja_samagri", "Purification and radiant blessing applied during Halad Chadavane", "Halad Chadavane"),
            ("Shriphal (Coconuts with Water)", "नारळ (श्रीफळ)", "11 pieces with tuft", "offerings", "Supreme auspicious offering to Varuna and Agni", "Vivah Homa"),
            ("Pure Cow Ghee", "शुद्ध गायीचे तूप", "1.5 kg", "sacred_fuel", "Divine oblation into sacred Vivah Agni during Laja Homa and Saptapadi", "Vivah Homa"),
            ("Laja (Puffed Rice)", "लाह्या", "500 grams", "offerings", "Poured into holy fire by bride with brother's assistance for prosperity and lineage", "Laja Homa"),
            ("Saptapadi Betel Nuts & Rice Piles", "सप्तपदी सुपाऱ्या", "7 nuts and 7 small rice heaps", "puja_samagri", "Marks the seven sacred marital vows taken around the fire", "Saptapadi"),
        ]
    },
    {
        "code": "punjabi_traditional",
        "regional_name": "Punjabi Traditional Vivah / Anand Karaj",
        "description": "Vibrant Punjabi celebration featuring Anand Karaj / Vedic Vivah, Maiyan, Jaggo, and Milni.",
        "cultural_notes": "Characterized by Chooda ceremony, Kalire tying, energetic Jaggo night, Milni elder embrace, and 4 Laavan/Pheras.",
        "is_verified": True,
        "verification_source": "Punjabi Purohit Sabha & Sikh Rehat Maryada",
        "items": [
            ("Chooda & Kalire Set", "ਚੂੜਾ ਅਤੇ ਕਲੀਰੇ", "1 set red/ivory bangles + 2 umbrella kalire", "bridal_adornment", "Given by maternal uncles and sisters, blessing the bride with joy and prosperity", "Chooda Ceremony"),
            ("Vatna Ubtan Paste", "ਵਟਣਾ", "500 grams mustard oil, besan, haldi, rosewater", "cleansing_pastes", "Applied by loved ones for ceremonial bridal and groom glow", "Maiyan"),
            ("Rumalla Sahib / Brocade Wrap", "ਰੁਮਾਲਾ ਸਾਹਿਬ", "2 fine silk and embroidered wraps", "sacred_offering", "Offered with humility to the altar or Guru Granth Sahib Ji", "Anand Karaj / Vivah"),
            ("Palla / Scarf for Pheras", "ਪੱਲਾ", "1 embroidered palla scarf", "ceremonial_fabrics", "Held by bride following the groom during the 4 sacred circumambulations", "4 Laavan / Pheras"),
            ("Degh / Karah Parshad Offering", "ਕੜਾਹ ਪ੍ਰਸਾਦ", "2.5 kg sanctified wheat flour, ghee, sugar sweet", "sacred_edibles", "Distributed to the congregation as divine blessing of grace", "Anand Sahib & Ardas"),
            ("Milni Woolen Shawls & Garlands", "ਮਿਲਣੀ ਦੋਸ਼ਾਲੇ", "5 sets shawls and fresh floral garlands", "welcome_customs", "Exchanged between counterpart male elders of bride and groom families", "Milni"),
            ("Jaggo Brass Lamp Vessel", "ਜਾਗੋ", "1 traditional brass pot with LED/dough lamps", "cultural_props", "Carried on head during lively nighttime pre-wedding revelry", "Jaggo Night"),
            ("Red Chunni / Phulkari Dupatta", "ਲਾਲ ਚੁੰਨੀ", "1 ceremonial embroidered dupatta", "ceremonial_fabrics", "Presented by groom's mother to the bride during Chunni Charhai", "Chunni Charhai"),
            ("Pure Desi Ghee", "ਦੇਸੀ ਘਿਓ", "1.5 kg", "sacred_fuel", "Oblations into the holy fire or preparation of sacred parshad", "Vivah Homa / Parshad"),
        ]
    },
    {
        "code": "bengali_vedic",
        "regional_name": "Bengali Vedic Bibaho",
        "description": "Lyrical Bengali Hindu wedding rituals blending Shakta, Vaishnava, and Vedic streams.",
        "cultural_notes": "Noted for Gaye Holud, Boron welcoming, Saat Paake Ghomar, Shubho Drishti eye-contact, Mala Badal, and Sindoor Daan.",
        "is_verified": True,
        "verification_source": "Bhattacharya Purohit Darpan & Bengal Purohit Samhita",
        "items": [
            ("Topor & Mukut Set", "টোপোর ও মুকুট", "1 white sholapith topor + 1 bride mukut", "bridal_adornment", "Conical white headdresses symbolizing dignity, grace, and purity", "Bibaho Arrival"),
            ("Paan Leaves (Betel Leaves)", "পানের পাতা", "21 large, flawless betel leaves", "ceremonial_props", "Bride covers her face with two leaves until the dramatic Shubho Drishti reveal", "Shubho Drishti"),
            ("Gachh Kouto (Vermilion Container)", "গাছ কৌটো", "1 carved wooden/lac red container with coins", "sacred_props", "Carried continuously by bride from Gaye Holud until she arrives at new home", "Bibaho Vidhi"),
            ("Shankha & Pola Bangles", "শাঁখা ও পলা", "1 pair white conch bangles + 1 pair red coral bangles", "bridal_adornment", "Quintessential signs of married Bengali Hindu women symbolizing coolness and warmth", "Saat Paake Ghomar"),
            ("Boron Dala (Welcome Tray)", "বরণ ডালা", "1 bamboo winnow tray with 12 auspicious elements", "welcome_customs", "Used by mother of the bride to welcome and bless the groom", "Boron"),
            ("Alta Botanical Red Dye", "আলতা", "2 bottles red cosmetic lac dye", "cleansing_pastes", "Delicately painted onto bride's palms, feet borders, and soles", "Gaye Holud"),
            ("Khoi (Puffed Paddy)", "খই", "1.5 kg", "offerings", "Offered by the couple from a kula (bamboo tray) into the fire (Kusumdinge)", "Khoi Phele"),
            ("Pure Mustard Oil & Turmeric", "সর্ষের তেল ও হলুদ", "500 ml raw mustard oil + 250g turmeric paste", "cleansing_pastes", "Applied in Gaye Holud blessing ceremony", "Gaye Holud"),
            ("Ganga Jal (Holy River Water)", "গঙ্গাজল", "1 litre sealed copper vessel", "puja_samagri", "Sprinkled for sanctification of the sampradan altar", "Sampradan"),
        ]
    },
    {
        "code": "tamil_brahmin_hindu",
        "regional_name": "Tamil Brahmin Iyer Kalyanam",
        "description": "Vedic Tamil Brahmin marriage rites adhering to Apastamba Grihya Sutra.",
        "cultural_notes": "Highlights include Vratham, Kasi Yatra, Oonjal swing songs, Kanyadaanam on father's lap, Mangalya Dharanam, and Nalangu.",
        "is_verified": True,
        "verification_source": "Apastamba Grihya Sutra & Vadhyar Vidhi Manual",
        "items": [
            ("Kasi Yatra Set", "காசி யாத்திரை செட்", "1 umbrella, walking stick, fan, Gita book", "custom_props", "Mock bachelor pilgrimage halted by bride's father offering grihastha life", "Kasi Yatra"),
            ("Koora Pudavai (Madisar Saree)", "கூறைப் புடவை", "1 nine-yard silk saree in turmeric red", "bridal_adornment", "Sacred bridal attire worn for the core Mangalya Dharanam moment", "Mangalya Dharanam"),
            ("Mangalyam / Thali & Manjal Charadu", "மாங்கல்யம் / மஞ்சள் கயிறு", "Gold Thali on turmeric-dyed yellow cord", "sacred_ornaments", "Sacred pendant tied around bride's neck with three knots representing mind, speech, deed", "Mangalya Dharanam"),
            ("Paruppu Thengai Kutti", "பருப்பு தேங்காய் கூம்பு", "1 pair of sweet cone towers", "auspicious_edibles", "Traditional sweet cone towers presented by both families at each ceremony", "Oonjal"),
            ("Akshathai (Blessed Yellow Rice)", "அக்ஷதை", "3 kg unbroken rice with turmeric and ghee", "puja_samagri", "Sprinkled by Vadhyar and assembly over couple during Thali tying", "Mangalya Dharanam"),
            ("Pori (Puffed Paddy)", "நெல் பொரி", "1.5 kg", "offerings", "Offered into the Agni kundam during Laja Homam by bride with brother's help", "Laja Homam"),
            ("Ammi Kal (Grindstone)", "அம்மிக்கல்", "1 traditional stone slab", "ceremonial_props", "Bride places right foot on stone (Asmarohana) signifying steadfast rock-like devotion", "Saptapadi"),
            ("Darbha Grass Bundles", "தர்பைப் புல்", "5 bundles sacred kusa grass", "puja_samagri", "Purification seats and sacred Pavithram finger rings for the homam", "Vratham"),
            ("Pure Cow Ghee", "பசு நெய்", "2 kg", "sacred_fuel", "Oblations to Indra, Varuna, and Agni in Pradhana Homam", "Vivah Homam"),
            ("Nalangu Turmeric & Rosewater", "நலங்கு சந்தனம் & பன்னீர்", "2 bowls turmeric paste + 1 rosewater sprinkler", "playful_rituals", "Evening playful singing and bonding games between bride and groom", "Nalangu"),
        ]
    },
    {
        "code": "gujarati_hindu",
        "regional_name": "Gujarati Hindu Vivah",
        "description": "Joyous Gujarati Vivah customs celebrating familial bond, Grah Shanti, and Pokhana groom welcome.",
        "cultural_notes": "Distinguished by Gol Dhana, Mandap Mahurat, Mameru/Mosalu gifts, Pokhana, and 4 Mangal Pheras.",
        "is_verified": True,
        "verification_source": "Gujarat Brahmin Sabha Ritual Compendium",
        "items": [
            ("Gol Dhana (Jaggery & Coriander Seeds)", "ગોળ ધાણા", "1 kg jaggery + 500g coriander seeds", "auspicious_edibles", "Distributed to celebrate commitment and sweet harmony between families", "Gol Dhana"),
            ("Pokhana Welcome Kit (Raval)", "પોંખણું", "1 set (mini mortar, pestle, churner, yoke)", "welcome_customs", "Mother-in-law playful test to groom to remind him of patience and domestic responsibility", "Pokhana"),
            ("Kankoo & Chodi", "કંકુ અને સોપારી", "250 grams red vermilion + 21 supari", "puja_samagri", "Sacred tilak and divine invocation during Mandap Mahurat", "Mandap Mahurat"),
            ("Hastamelap Cord & Cloth", "હસ્તમેળાપ કાપડ", "1 white/red sacred cord with beetle coin", "ceremonial_fabrics", "Tying the groom's right hand to the bride's right hand in eternal union", "Hastamelap"),
            ("Kansar Sweet Offering", "કાંસાર", "500 grams sweet wheat/ghee preparation", "sacred_edibles", "First sweet food lovingly fed by newly wedded couple to one another", "Kansar Vidhi"),
            ("Coda Codi Silver Bowl & Coins", "કોડા કોડી વાટકો", "1 silver bowl with milk, water, ring, cowries", "playful_rituals", "Couple fishes for the ring to decide domestic harmony and playful mastery", "Coda Codi"),
            ("Shriphal (Dry & Fresh Coconuts)", "શ્રીફળ", "15 pieces", "offerings", "Given with blessing envelopes to maternal and paternal elders", "Mosalu & Mameru"),
            ("Navgraha Samidha Havan Wood", "નવગ્રહ સમિધા", "9 sets of planetary wood sticks", "sacred_fuel", "Appeasement of the nine planetary forces for a peaceful marital life", "Grah Shanti"),
            ("Cow Ghee for Havan", "દેશી ગાયનું ઘી", "1.5 kg", "sacred_fuel", "Oblations offered during Vivah Homam and Mangal Pheras", "Mangal Pheras"),
            ("Antarpat with Ganesha", "અંતરપટ", "1 silk cloth with gold brocade", "ceremonial_fabrics", "Hides the bride until auspicious kanyadaan ascendant moment", "Hastamelap"),
        ]
    },
    {
        "code": "muslim_nikah",
        "regional_name": "Muslim Traditional Nikah",
        "description": "Solemn Islamic marriage covenant governed by the Shariah and rich South Asian cultural customs.",
        "cultural_notes": "Distinguished by Manjha (Haldi), Istiqbal welcome, Ijab-o-Qubool (offer and acceptance), Mehr settlement, Arsi Mushaf, and Walima reception.",
        "is_verified": True,
        "verification_source": "All India Muslim Personal Law Board & Islamic Nikahnama Guidelines",
        "items": [
            ("Nikahnama Document & Presentation Quill", "نکاح نامہ", "1 official marriage contract ledger + calligraphic pen", "legal_sacred_document", "Signed by the couple, Qazi, and two male witnesses formalizing the marriage covenant", "Nikah Ijab-o-Qubool"),
            ("Mehr Settlement Protocol & Envelope", "مہر", "Formal dower declaration ledger + velvet presentation case", "marital_covenant", "Mandatory financial security gifted directly by the groom to the bride", "Nikah"),
            ("Arsi Mushaf Mirror & Holy Quran", "آرسی مصحف", "1 ornate silver mirror + Holy Quran with velvet stand", "ceremonial_props", "The couple glances at each other's reflection for the first time as spouses under a sheer veil", "Arsi Mushaf"),
            ("Pure Attar (Rose & Oudh)", "عطر", "2 crystal flacons non-alcoholic attar", "hospitality_fragrance", "Dabbed on guests' wrists as a mark of royal Mughal hospitality and welcome", "Istiqbal / Baraat"),
            ("Cardamom, Misri & Paan Cones", "الائچی اور مصری", "1 ornate silver tray with cardamom pods, candied misri, paan", "auspicious_edibles", "Distributed to the entire congregation following the Qazi's Khutbah and Dua", "Post-Nikah Shukrana"),
            ("Groom Floral Sehra", "سہرا", "1 floral veil made of fresh jasmine and rosebuds", "groom_adornment", "Tied across groom's safa/turban before departing for the wedding venue", "Baraat Departure"),
            ("Kishmish & Almond Milk (Shir Khurma)", "شیر خرما", "2 silver goblets warm almond-saffron milk", "ceremonial_edibles", "Shared by the bride and groom following the completion of the Nikah vows", "Rukhsati / Welcome"),
        ]
    },
    {
        "code": "christian_traditional",
        "regional_name": "Indian Christian Traditional Wedding",
        "description": "Reverent Christian Holy Matrimony integrating church liturgy with Indian cultural motifs (Minnu/Manthrakodi).",
        "cultural_notes": "Features Church Nuptial Blessing, Exchange of Vows and Rings, Minnu (Thali) tying, Manthrakodi bridal gifting, and Gala Reception.",
        "is_verified": True,
        "verification_source": "Church Liturgical Commission & Catholic/CSI Holy Matrimony Order",
        "items": [
            ("Blessed Wedding Rings", "Blessed Rings", "2 engraved gold/platinum rings in velvet box", "sacred_symbols", "Blessed by officiating priest/pastor symbolizing eternal fidelity and covenant", "Exchange of Rings"),
            ("Minnu / Christian Thali & 7-Thread Cord", "മിന്ന് / தாலி", "1 gold tear-drop pendant with cross + thread woven from Manthrakodi saree", "sacred_ornaments", "Tied around bride's neck by groom representing cultural and spiritual union", "Solemnization"),
            ("Manthrakodi Bridal Silk Saree", "മന്ത്രകോടി", "1 rich silk saree blessed at the altar", "bridal_adornment", "Draped over bride's head by groom signifying his lifelong protection and care", "Nuptial Blessing"),
            ("Church Altar & Unity Candles", "Unity Candles", "1 master pillar candle + 2 taper candles with floral wreaths", "liturgical_props", "Lit by the bride and groom together symbolizing two independent lives merged in Christ", "Service of Light"),
            ("Holy Bible Keepsake Edition", "Wedding Bible", "1 leather/gold embossed family Bible", "sacred_scripture", "Presented to the newlyweds to guide their domestic household", "Blessing of Household"),
            ("Roce Blessing Oil & Coconut Milk", "Roce / Haldi Bath", "1 bowl fresh coconut milk and rose petals", "cleansing_pastes", "Applied by maternal elders on eve of wedding symbolizing purification and blessing", "Roce Eve"),
            ("Champagne / Sparkling Toast Flutes", "Toast Flutes", "2 crystal champagne flutes + bottle for toast", "celebration", "Raised during the Best Man and Father-of-the-Bride reception toasts", "Reception Banquet"),
        ]
    },
    {
        "code": "telugu_hindu",
        "regional_name": "Telugu Vaidika Kalyanam",
        "description": "Graceful Telugu Hindu marriage rituals focused on mutual equality and Vedic vows.",
        "cultural_notes": "Characterized by Pellikuthuru, Snathakam, Jeelakarra Bellam at exact muhurat, Mangalsutra Dharana, and celebratory Talambralu.",
        "is_verified": True,
        "verification_source": "Telugu Vaidika Dharma Shastra & Kalyana Vidhanam",
        "items": [
            ("Jeelakarra & Bellam Paste", "జీలకర్ర మరియు బెల్లం", "1 paste of cumin seeds and jaggery", "auspicious_edibles", "Placed on each other's head at the exact auspicious Muhurat fraction of a second", "Jeelakarra Bellam"),
            ("Talambralu Sacred Rice / Pearls", "తలంబ్రాలు", "5 kg rice mixed with turmeric, rosewater, pearls", "puja_samagri", "Joyously showered over each other's heads by bride and groom", "Talambralu"),
            ("Madhuparkam Khadi Garments", "మధుపర్కం", "1 white dhoti/saree set with red/yellow border", "bridal_adornment", "Purity cotton attire worn during Kanyadanam and Jeelakarra Bellam", "Kanyadanam"),
            ("Mangalsutra (Two Gold Sutrams)", "మంగళసూత్రం (పుస్తేలు)", "2 round gold discs on yellow string", "sacred_ornaments", "One from maternal side, one from groom's side, tied with three knots", "Mangalsutra Dharana"),
            ("Mettelu (Toe Rings)", "మెట్టెలు", "2 silver toe rings for second toes", "sacred_ornaments", "Slipped onto bride's feet by groom on the grinding stone (Sannikallu)", "Saptapadi"),
            ("Garika Muntha (Sacred Painted Pot)", "గరిక ముంత", "1 hand-painted terracotta pot with lid", "ceremonial_props", "Carried by bride's maternal aunt to the vivaha mandapam", "Mandapam Entry"),
            ("Nalla Pusalu (Black Beads)", "నల్లపూਸలు", "1 strand black glass beads", "sacred_ornaments", "Warded against evil eye, worn along with the Mangalasutram", "Kalyanam"),
            ("Cow Ghee for Homam", "ఆవు నెయ్యి", "2 kg pure cow ghee", "sacred_fuel", "Poured into the sacred Vivaha Homa fire by the vadhyar", "Vivaha Homam"),
        ]
    }
]


def seed_cultural_traditions(db=None):
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        traditions_seeded = 0
        items_seeded = 0

        for t_data in CURATED_TRADITIONS:
            existing_tradition = db.query(Tradition).filter(Tradition.code == t_data["code"]).first()
            if existing_tradition:
                existing_tradition.regional_name = t_data["regional_name"]
                existing_tradition.description = t_data["description"]
                existing_tradition.cultural_notes = t_data["cultural_notes"]
                existing_tradition.is_verified = t_data["is_verified"]
                existing_tradition.verification_source = t_data["verification_source"]
            else:
                tradition_obj = Tradition(
                    code=t_data["code"],
                    regional_name=t_data["regional_name"],
                    description=t_data["description"],
                    cultural_notes=t_data["cultural_notes"],
                    is_verified=t_data["is_verified"],
                    verification_source=t_data["verification_source"]
                )
                db.add(tradition_obj)
                traditions_seeded += 1
            
            # Clear existing items for clean deterministic seed
            db.query(RitualItem).filter(RitualItem.tradition_code == t_data["code"]).delete()

            for item_name, regional_name, qty, category, purpose, ritual_name in t_data["items"]:
                r_item = RitualItem(
                    tradition_code=t_data["code"],
                    item_name=item_name,
                    regional_name=regional_name,
                    standard_quantity=qty,
                    category=category,
                    spiritual_purpose=purpose,
                    ritual_name=ritual_name,
                    is_verified=t_data["is_verified"]
                )
                db.add(r_item)
                items_seeded += 1

        db.commit()
        return {
            "status": "success",
            "traditions_configured": len(CURATED_TRADITIONS),
            "ritual_items_seeded": items_seeded,
        }
    except Exception as e:
        db.rollback()
        raise e
    finally:
        if close_db:
            db.close()


if __name__ == "__main__":
    res = seed_cultural_traditions()
    print("Seed complete:", res)
