"""TPAS Form 6 - Student Evaluation of Teachers (content of the form).

Item wording is kept exactly as in the school's form (he/she wording untouched).
Only three typos were corrected: "leaned" -> "learned", "a person interest" ->
"a personal interest", "helps student" -> "helps students".
"""

FORM_CODE = "TPAS-6"
FORM_TITLE = "Student Evaluation of Teachers"

# rating -> label (5 is best)
SCALE = {5: "Consistently", 4: "Frequently", 3: "Occasionally", 2: "Rarely", 1: "Very Rarely"}

CATEGORIES = [
    {
        "code": "A",
        "name": "Knowledge of Subject & Teaching Style",
        "short": "A. Knowledge & Teaching Style",
        "items": [
            "has very good knowledge of the subject he/she teaches.",
            "is organized and prepared for class.",
            "uses learning materials like power point presentations, pictures, charts, illustrations, etc. to help students understand the lesson.",
            "presents the lesson in an understandable way.",
            "uses clear examples and emphasizes important points in the lesson.",
            "adjusts her ways of teaching to the students\u2019 learning abilities.",
        ],
    },
    {
        "code": "B",
        "name": "Interest and Stimulation",
        "short": "B. Interest & Stimulation",
        "items": [
            "shows enthusiasm about the subject he teaches.",
            "helps students to think independently.",
            "uses a variety of teaching styles and techniques.",
            "makes sure that class lessons and discussions are interesting, enjoyable, worthwhile and challenging.",
            "lets students tell him/her what they think or feel about the lesson.",
            "gives favorable and encouraging comments when students give correct answers or good ideas.",
        ],
    },
    {
        "code": "C",
        "name": "Class Management and Organization",
        "short": "C. Class Management",
        "items": [
            "speaks fluently and clearly.",
            "starts and ends classes on time.",
            "establishes clear guidelines for quizzes, tests and papers.",
            "promptly informs the students of the results of tests and assignments.",
            "grades students fairly, based on how much they have actually learned or done.",
            "sees to it that all students obey school rules and regulations.",
            "maintains a reasonable level of order and discipline in class.",
            "makes sure that the classroom is always clean and orderly, shows proper care for school property.",
        ],
    },
    {
        "code": "D",
        "name": "Teacher-Student Relations",
        "short": "D. Teacher-Student Relations",
        "items": [
            "makes the students feel free to ask questions.",
            "is fair in dealing with students.",
            "is available to students for guidance and assistance even outside class time.",
            "shows a personal interest in students\u2019 progress and success.",
            "reminds students about proper behavior at all times.",
            "is pleasant, patient, amiable and mild tempered.",
            "reminds students to show respect and care for other people.",
            "reminds students of their responsibilities as good and worthy members of the community.",
        ],
    },
]

# Flat list of (item_no, category_code, text); item_no runs 1..28
ITEMS = []
for _cat in CATEGORIES:
    for _text in _cat["items"]:
        ITEMS.append((len(ITEMS) + 1, _cat["code"], _text))

ITEM_CAT = {no: code for no, code, _ in ITEMS}
ITEM_TEXT = {no: text for no, _, text in ITEMS}
CAT_CODES = [c["code"] for c in CATEGORIES]
CAT_NAME = {c["code"]: c["name"] for c in CATEGORIES}
CAT_SHORT = {c["code"]: c["short"] for c in CATEGORIES}
ITEM_NUMBERS = [no for no, _, _ in ITEMS]

# (column in `responses`, label)
COMMENT_FIELDS = [
    ("comment_strategy", "Teaching Strategy"),
    ("comment_management", "Classroom Management"),
    ("comment_others", "Others (please specify)"),
]

SEMESTERS = ["1st Semester", "2nd Semester"]
GRADE_LEVELS = ["Grade 11", "Grade 12"]  # Senior High School
