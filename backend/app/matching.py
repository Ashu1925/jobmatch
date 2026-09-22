import string


KNOWN_SKILLS = {
    "python",
    "fastapi",
    "django",
    "flask",
    "javascript",
    "typescript",
    "react",
    "angular",
    "vue",
    "html",
    "css",
    "sql",
    "postgresql",
    "mysql",
    "mongodb",
    "docker",
    "kubernetes",
    "aws",
    "azure",
    "git",
    "rest api",
    "machine learning",
    "data analysis",
    "pandas",
    "numpy",
    "java",
    "spring",
    "spring boot",
    "hibernate",
    "jpa",
    "microservices",
    "openshift",
    "devops",
    "oop",
    "solid",
}


SKILL_ALIASES = {
    "rest api": {
        "rest api",
        "rest apis",
        "restful api",
        "restful apis",
        "restful web services",
    },
    "spring": {
        "spring",
        "spring framework",
    },
    "spring boot": {
        "spring boot",
    },
    "microservices": {
        "microservice",
        "microservices",
        "microservices architecture",
    },
    "openshift": {
        "openshift",
        "openshift container platform",
    },
    "ci/cd": {
        "ci cd",
        "continuous integration",
        "continuous delivery",
        "continuous deployment",
    },
    "oop": {
        "oop",
        "object oriented programming",
        "object oriented concepts",
    },
    "solid": {  
        "solid",
        "solid principles",
    },
}


def normalize_text(text: str) -> str:
    lowercase_text = text.lower()

    punctuation_to_spaces = str.maketrans(
        string.punctuation,
        " " * len(string.punctuation),
    )

    text_without_punctuation = lowercase_text.translate(
        punctuation_to_spaces
    )

    normalized_text = " ".join(
        text_without_punctuation.split()
    )

    return normalized_text


def extract_skills(text: str) -> set[str]:
    normalized_text = normalize_text(text)
    padded_text = f" {normalized_text} "
    extracted_skills: set[str] = set()

    for skill in KNOWN_SKILLS:
        padded_skill = f" {skill} "

        if padded_skill in padded_text:
            extracted_skills.add(skill)

    for canonical_skill, aliases in SKILL_ALIASES.items():
        for alias in aliases:
            normalized_alias = normalize_text(alias)
            padded_alias = f" {normalized_alias} "

            if padded_alias in padded_text:
                extracted_skills.add(canonical_skill)
                break

    return extracted_skills


def calculate_match(
    resume_text: str,
    job_description: str,
) -> dict:
    resume_skills = extract_skills(resume_text)
    job_skills = extract_skills(job_description)

    matching_skills = resume_skills.intersection(job_skills)
    missing_skills = job_skills.difference(resume_skills)

    if not job_skills:
        match_score = 0
    else:
        match_score = round(
            len(matching_skills) / len(job_skills) * 100
        )

    return {
        "match_score": match_score,
        "matching_skills": sorted(matching_skills),
        "missing_skills": sorted(missing_skills),
    }
