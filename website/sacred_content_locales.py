"""
Localized SACRED homepage and goal page copy.

Sourced from tipitakahall.org Omeka scripts:
``scripts/lib/sacred-homepage.php``, ``sacred-goal-pages.php``,
and ``catalog/corpus-types.csv``.
"""

from __future__ import annotations

from typing import NotRequired, TypedDict


class PrincipleCase(TypedDict):
    mark: str
    body: str


class GoalCard(TypedDict):
    number: str
    title: str
    abstract: str
    slug: str
    link_label: str
    # Optional page slug for the card CTA (defaults to ``slug`` / goal detail page).
    link_slug: NotRequired[str]


class ClassificationEntry(TypedDict):
    siglum: str
    title: str
    description: str


class GoalPage(TypedDict):
    slug: str
    title: str
    paragraphs: tuple[str, ...]
    search_description: str


class LocaleContent(TypedDict):
    fullname: str
    mission_title: str
    mission_body: str
    principle_title: str
    principle_body: str
    principle_cases: tuple[PrincipleCase, PrincipleCase]
    goals_title: str
    goals: tuple[GoalCard, GoalCard, GoalCard]
    classification_heading: str
    classification_cta: str
    classification_entries: tuple[ClassificationEntry, ...]
    home_search_description: str
    goal_pages: tuple[GoalPage, ...]


LOCALE_CONTENT: dict[str, LocaleContent] = {
    "en": {
        "fullname": "The People's Tipiṭaka Hall",
        "mission_title": "Mission",
        "mission_body": (
            "Conserving and safeguarding the integrity of the Tipiṭaka<br>\n"
            "carrying forward a tradition of textual preservation spanning over 2,500 years<br>\n"
            "from oral recitation, palm-leaf manuscripts, and printed books<br>\n"
            "to the digital and AI era<br>\n"
            "to sustain the wisdom heritage of humanity"
        ),
        "principle_title": "Principle · The Four Great Authorities",
        "principle_body": (
            "When one claims that<br>\n"
            "&ldquo;This is the Doctrine, this is the Discipline, this is the Master&rsquo;s teaching&rdquo;<br>\n"
            "the words of that person are neither to be welcomed nor scorned<br>\n"
            "the words and syllables thereof are to be studied thoroughly<br>\n"
            "laid beside the Discourses and compared with the Discipline"
        ),
        "principle_cases": (
            {
                "mark": "a.",
                "body": (
                    "If, when laid beside the Discourses and compared with the Discipline,<br>\n"
                    "these words and syllables lie not along with the Discourses<br>\n"
                    "and agree not with the Discipline,<br>\n"
                    "then you may come to the conclusion:<br>\n"
                    "Surely this is not the word of the Blessed One"
                ),
            },
            {
                "mark": "b.",
                "body": (
                    "If, when laid beside the Discourses and compared with the Discipline,<br>\n"
                    "these words and syllables lie along with the Discourses<br>\n"
                    "and agree with the Discipline,<br>\n"
                    "then you may come to the conclusion:<br>\n"
                    "Surely this is the word of the Blessed One"
                ),
            },
        ),
        "goals_title": "Goals",
        "goals": (
            {
                "number": "1",
                "title": "Tipiṭaka Repository",
                "abstract": "Collect and preserve principal Theravāda Tipiṭaka editions.",
                "slug": "goal-repository",
                "link_slug": "buddhist-scriptures",
                "link_label": "Read more",
            },
            {
                "number": "2",
                "title": "Cross-Edition Unity",
                "abstract": "A master table of contents and unified reference system.",
                "slug": "goal-cross-edition",
                "link_label": "Read more",
            },
            {
                "number": "3",
                "title": "Mahāpadesa Verification",
                "abstract": "Search, verify, and compare against the Doctrine and Discipline.",
                "slug": "goal-mahapadesa",
                "link_label": "Read more",
            },
        ),
        "classification_heading": "Classification",
        "classification_cta": "Browse collection",
        "classification_entries": (
            {
                "siglum": "TP",
                "title": "Tipiṭaka",
                "description": (
                    "The principal scriptures recording the Buddha's teachings (Buddhavacana), "
                    "divided into three sections: Vinaya, Sutta, and Abhidhamma."
                ),
            },
            {
                "siglum": "AK",
                "title": "Aṭṭhakathā",
                "description": (
                    "Scriptures that explain the meaning of the Tipiṭaka, clarifying difficult "
                    "terms and doctrines."
                ),
            },
            {
                "siglum": "TK",
                "title": "Ṭīkā",
                "description": (
                    "Scriptures that further explain the commentaries, going deeper to resolve "
                    "questions raised in those explanations."
                ),
            },
            {
                "siglum": "AN",
                "title": "Añña",
                "description": (
                    "Other secondary scriptures, including yojanā, gaṇṭhi, dīpanī, atthayojanā, "
                    "pakaraṇavisesa, saddā, and the like."
                ),
            },
        ),
        "home_search_description": (
            "The People's Tipiṭaka Hall (SACRED) conserves Theravāda Tipiṭaka editions, "
            "cross-edition references, and Mahāpadesa verification tools."
        ),
        "goal_pages": (
            {
                "slug": "goal-repository",
                "title": "Tipiṭaka Repository",
                "paragraphs": (
                    "SACRED gathers and preserves principal Theravāda Tipiṭaka editions "
                    "transmitted through the Buddhist Councils, in full across nations.",
                    "Reference editions such as Chaṭṭha Saṅgāyana, Syāmaraṭṭha, "
                    "Mahāchulalongkorn, and Buddhajayantī are archived in a unified digital "
                    "form so that the textual heritage of each tradition remains accessible "
                    "and intact.",
                    "This repository is the foundation of every cross-edition reference and "
                    "Mahāpadesa verification on the site.",
                ),
                "search_description": "Collect and preserve principal Theravāda Tipiṭaka editions.",
            },
            {
                "slug": "goal-cross-edition",
                "title": "Cross-Edition Unity",
                "paragraphs": (
                    "A master table of contents links volumes and texts across every "
                    "reference edition in SACRED.",
                    "A unified reference system lets readers locate the same passage in "
                    "different editions and compare readings side by side, with textual "
                    "differences shown transparently.",
                    "Cross-edition unity makes the international repository practically "
                    "useful for study, scholarship, and verification.",
                ),
                "search_description": "A master table of contents and unified reference system.",
            },
            {
                "slug": "goal-mahapadesa",
                "title": "Mahāpadesa Verification",
                "paragraphs": (
                    "Analytical tools for Dhamma passages help readers search the Tipiṭaka "
                    "and examine whether a teaching aligns with the Doctrine and Discipline.",
                    "Following the Mahāpadesa principle, claims are neither accepted nor "
                    "rejected at once: words are studied, laid beside the Discourses, and "
                    "compared with the Vinaya before a conclusion is drawn.",
                    "AI-assisted search and citation support this process, always grounding "
                    "answers in the archived editions.",
                ),
                "search_description": (
                    "Search, verify, and compare against the Doctrine and Discipline."
                ),
            },
        ),
    },
    "th": {
        "fullname": "หอพระไตรปิฎกเพื่อประชาชน",
        "mission_title": "พันธกิจ",
        "mission_body": (
            "อนุรักษ์และรักษาความถูกต้องของพระไตรปิฎก<br>\n"
            "สานต่อกระบวนการรักษาพระคัมภีร์ที่ดำเนินมากว่า ๒,๕๐๐ ปี<br>\n"
            "จากยุคมุขปาฐะ จารใบลาน พิมพ์หนังสือ สู่ยุคดิจิทัลปัญญาประดิษฐ์<br>\n"
            "เพื่อสืบทอดคลังอารยธรรมทางปัญญาของมนุษยชาติ"
        ),
        "principle_title": "หลักการ · มหาปเทส ๔",
        "principle_body": (
            "เมื่อมีผู้กล่าวอ้างว่า<br>\n"
            "“นี้เป็นธรรม นี้เป็นวินัย นี้เป็นสัตถุสาสน์”<br>\n"
            "เธอทั้งหลาย ยังไม่พึงชื่นชม ยังไม่พึงคัดค้านคำกล่าวอ้างของผู้นั้น<br>\n"
            "พึงเรียนบทและพยัญชนะเหล่านั้นให้ดีแล้ว<br>\n"
            "พึงสอบดูในพระสูตรเทียบดูในพระวินัย"
        ),
        "principle_cases": (
            {
                "mark": "ก.",
                "body": (
                    "ถ้าบทและพยัญชนะเหล่านั้น<br>\n"
                    "สอบลงในพระสูตรก็ไม่ได้ เทียบเข้าในพระวินัยก็ไม่ได้<br>\n"
                    "พึงลงสันนิษฐานว่า นี้มิใช่ดำรัสของพระผู้มีพระภาคแน่นอน"
                ),
            },
            {
                "mark": "ข.",
                "body": (
                    "ถ้าบทและพยัญชนะเหล่านั้น<br>\n"
                    "สอบลงในพระสูตรก็ได้ เทียบเข้าในพระวินัยก็ได้<br>\n"
                    "พึงลงสันนิษฐานว่า นี้เป็นดำรัสของพระผู้มีพระภาคแน่แท้"
                ),
            },
        ),
        "goals_title": "เป้าหมาย",
        "goals": (
            {
                "number": "๑",
                "title": "คลังพระไตรปิฎก",
                "abstract": "รวบรวมและอนุรักษ์พระไตรปิฎกเถรวาทชุดสำคัญ",
                "slug": "goal-repository",
                "link_slug": "buddhist-scriptures",
                "link_label": "อ่านเพิ่มเติม",
            },
            {
                "number": "๒",
                "title": "เอกภาพการอ้างอิงข้ามฉบับ",
                "abstract": "สารบัญกลางและระบบอ้างอิงร่วม",
                "slug": "goal-cross-edition",
                "link_label": "อ่านเพิ่มเติม",
            },
            {
                "number": "๓",
                "title": "มหาปเทส ๔",
                "abstract": "สืบค้น ตรวจสอบ และเทียบเคียงกับพระธรรมและพระวินัย",
                "slug": "goal-mahapadesa",
                "link_label": "อ่านเพิ่มเติม",
            },
        ),
        "classification_heading": "ประเภทคัมภีร์",
        "classification_cta": "เข้าชมคลัง",
        "classification_entries": (
            {
                "siglum": "TP",
                "title": "พระไตรปิฎก",
                "description": (
                    "คัมภีร์ที่บรรจุพุทธพจน์ (และเรื่องราวชั้นเดิมของพระพุทธศาสนา) ๓ ชุด "
                    "หรือ ประมวลแห่งคัมภีร์ที่รวบรวมพระธรรมวินัย ๓ หมวด "
                    "คือ วินัยปิฎก สุตตันตปิฎก และ อภิธรรมปิฎก"
                ),
            },
            {
                "siglum": "AK",
                "title": "อฏฺฐกถา",
                "description": (
                    "คัมภีร์ที่อธิบายความหมายของพระไตรปิฎก "
                    "ช่วยขยายความคำศัพท์หรือหลักธรรมที่เข้าใจยากให้ชัดเจนขึ้น"
                ),
            },
            {
                "siglum": "TK",
                "title": "ฏีกา",
                "description": (
                    "คัมภีร์ที่อธิบายขยายความอรรถกถา อีกชั้นหนึ่ง "
                    "เพื่อแก้ข้อสงสัยในคำอธิบายของอรรถกถาให้ลึกซึ้งยิ่งขึ้น"
                ),
            },
            {
                "siglum": "AN",
                "title": "อญฺญา",
                "description": (
                    "คัมภีร์ระดับรองอื่น ๆ ครอบคลุม โยชนา, คัณฐี, ทีปนี, อัตถโยชนา, "
                    "ปกรณวิเสส และสัททา เป็นต้น"
                ),
            },
        ),
        "home_search_description": (
            "หอพระไตรปิฎก SACRED อนุรักษ์พระไตรปิฎกเถรวาท "
            "การอ้างอิงข้ามฉบับ และเครื่องมือตรวจสอบตามหลักมหาปเทส"
        ),
        "goal_pages": (
            {
                "slug": "goal-repository",
                "title": "คลังพระไตรปิฎก",
                "paragraphs": (
                    "หอพระไตรปิฎก SACRED รวบรวมและอนุรักษ์พระไตรปิฎกเถรวาทฉบับอ้างอิงหลักที่สืบทอดมาจากการสังคายนาทั่วโลก ไว้อย่างครบถ้วน",
                    "ฉบับอ้างอิง เช่น ฉัฏฐสังคายนา สยามรัฐ มหาจุฬาฯ และพุทธชยันตี จัดเก็บในรูปแบบดิจิทัลมาตรฐานเดียวกัน เพื่อให้มรดกพระคัมภีร์ของแต่ละประเทศเข้าถึงได้และคงอยู่ถาวร",
                    "คลังนี้เป็นฐานของการอ้างอิงข้ามฉบับและการตรวจสอบตามหลักมหาปเทสทั้งหมดบนเว็บไซต์",
                ),
                "search_description": "รวบรวมและอนุรักษ์พระไตรปิฎกเถรวาทชุดสำคัญ",
            },
            {
                "slug": "goal-cross-edition",
                "title": "เอกภาพการอ้างอิงข้ามฉบับ",
                "paragraphs": (
                    "สารบัญกลางเชื่อมโยงเล่มและพระสูตรข้ามทุกฉบับอ้างอิงในหอพระไตรปิฎก SACRED",
                    "ระบบอ้างอิงร่วมช่วยค้นหาบทเดียวกันในฉบับต่าง ๆ และเทียบอ่านคู่ขนานได้ โดยแสดงความต่างของข้อความอย่างโปร่งใส",
                    "เอกภาพการอ้างอิงข้ามฉบับทำให้คลังนานาชาติใช้งานได้จริงในการศึกษา วิชาการ และการตรวจสอบ",
                ),
                "search_description": "สารบัญกลางและระบบอ้างอิงร่วม",
            },
            {
                "slug": "goal-mahapadesa",
                "title": "มหาปเทส ๔",
                "paragraphs": (
                    "เครื่องมือวิเคราะห์บทธรรมะช่วยสืบค้นพระไตรปิฎกและตรวจสอบว่าคำสอนนั้นสอดคล้องกับพระธรรมและพระวินัยหรือไม่",
                    "ตามหลักมหาปเทส ๔ ยังไม่พึงชื่นชมหรือคัดค้านทันที แต่พึงเรียนบทให้ดี สอบดูในพระสูตรและเทียบดูในพระวินัยก่อนลงสันนิษฐาน",
                    "ระบบ AI ช่วยสืบค้นและอ้างอิงตามกระบวนการนี้ โดยยึดฉบับอ้างอิงในคลังเป็นหลักเสมอ",
                ),
                "search_description": "สืบค้น ตรวจสอบ และเทียบเคียงกับพระธรรมและพระวินัย",
            },
        ),
    },
}


def get_locale_content(language_code: str) -> LocaleContent:
    try:
        return LOCALE_CONTENT[language_code]
    except KeyError as exc:
        raise ValueError(f"Unsupported locale: {language_code!r}") from exc
