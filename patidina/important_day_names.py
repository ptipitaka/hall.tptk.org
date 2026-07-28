"""
English display names for Patidina important days.

Religious terms follow common Theravāda English usage
(Access to Insight, BuddhaNet, Sri Lankan monastic English):
Pali romanization kept for Vinaya calendar terms such as
purimikā / pacchimikā vassūpanāyikā.
"""

from __future__ import annotations

# Thai name (as stored) → English display name
IMPORTANT_DAY_NAME_EN: dict[str, str] = {
    # Lunar / Buddhist commemorative
    "วันพระอัครสาวกบรรพชา": "Ordination of the Chief Disciples",
    "วันพระโมคคัลานะสำเร็จเป็นพระอรหันต์": "Ven. Moggallāna attains arahatship",
    "วันมาฆบูชา": "Māgha Pūjā (Sangha Day)",
    "วันพระสารีบุตรสำเร็จเป็นพระอรหันต์": "Ven. Sāriputta attains arahatship",
    "วันเสร็จสิ้นการปฐมสังคายนา": "Conclusion of the First Council",
    "วันวิสาขบูชา": "Visākha Pūjā (Vesak)",
    "วันเสร็จโปรดพระประยูรญาติ": "Conclusion of teaching the Buddha’s relatives",
    "วันพระราหุลบรรพชา": "Ordination of Ven. Rāhula",
    "วันอัฏฐมีบูชา": "Aṭṭhamī Pūjā",
    "วันอาสาฬหบูชา": "Āsāḷha Pūjā (Dhamma Day)",
    "วันเข้าพรรษาแรก (ปุริมพรรษา)": (
        "Beginning of the earlier Rains Retreat (purimikā vassūpanāyikā)"
    ),
    "วันพระปัญจวัคคีย์สำเร็จเป็นพระอรหันต์": (
        "The Group of Five attains arahatship"
    ),
    "วันเข้าพรรษาหลัง (ปัจฉิมพรรษา)": (
        "Beginning of the later Rains Retreat (pacchimikā vassūpanāyikā)"
    ),
    "วันพระอานนท์สำเร็จเป็นพระอรหันต์": "Ven. Ānanda attains arahatship",
    "วันปฐมสังคายนา": "First Buddhist Council",
    "วันสารทไทย": "Thai Sart Day",
    "วันออกพรรษาแรก (ปุริมพรรษา)": (
        "End of the earlier Rains Retreat (purimikā / pavāraṇā)"
    ),
    "วันพระสาริบุตรปรินิพพาน": "Parinibbāna of Ven. Sāriputta",
    "วันออกพรรษาหลัง (ปัจฉิมพรรษา)": (
        "End of the later Rains Retreat (pacchimikā / pavāraṇā)"
    ),
    "วันลอยกระทง": "Loi Krathong",
    "วันพระโมคคัลานะปรินิพพาน": "Parinibbāna of Ven. Moggallāna",
    # Solar / national
    "วันขึ้นปีใหม่": "New Year’s Day",
    "วันจักรี": "Chakri Memorial Day",
    "วันมหาสงกรานต์": "Maha Songkran Day",
    "วันผู้สูงอายุแห่งชาติ": "National Elderly Day",
    "วันสงกรานต์ (วันเถลิงศก)": "Songkran (Wan Thaloeng Sok)",
    "วันสงกรานต์ (วันเนา)": "Songkran (Wan Nao)",
    "วันครอบครัว": "Family Day",
    "วันฉัตรมงคล": "Coronation Day",
    "วันเฉลิมพระชนมพรรษา สมเด็จพระนางเจ้าฯ พระบรมราชินี": (
        "Birthday of Queen Suthida"
    ),
    "วันเฉลิมพระชนมพรรษา พระบาทสมเด็จพระเจ้าอยู่หัว": (
        "Birthday of His Majesty the King"
    ),
    "วันเฉลิมพระชนมพรรษา พระบรมราชชนนีพันปีหลวง": (
        "Birthday of Queen Sirikit The Queen Mother"
    ),
    "วันแม่แห่งชาติ": "Mother’s Day",
    "วันนวมินทรมหาราช": "King Bhumibol Memorial Day",
    "วันปิยมหาราช": "Chulalongkorn Day",
    "วันมหาภูมิพลอดุลยเดชมหาราช": "King Bhumibol Adulyadej the Great Day",
    "วันชาติ": "National Day",
    "วันพ่อแห่งชาติ": "Father’s Day",
    "วันรัฐธรรมนูญ": "Constitution Day",
    "วันสิ้นปี": "New Year’s Eve",
}


def english_name_for(thai_name: str) -> str:
    return IMPORTANT_DAY_NAME_EN.get(thai_name, thai_name)
