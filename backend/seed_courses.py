from db.database import SessionLocal
from models.db_models import Course, CourseType

def seed():
    db = SessionLocal()
    if db.query(Course).count() > 0:
        print("Courses already exist.")
        return

    courses = [
        Course(name="B.Tech in Computer Science & Engineering", type=CourseType.UG, seats=120, fees=450000.0, eligibility_summary="Min 60% in 12th PCM"),
        Course(name="B.Tech in Information Technology", type=CourseType.UG, seats=60, fees=420000.0, eligibility_summary="Min 60% in 12th PCM"),
        Course(name="M.Tech in Computer Science", type=CourseType.PG, seats=30, fees=200000.0, eligibility_summary="B.Tech in CSE/IT with 6.5 CGPA"),
        Course(name="BCA (Bachelor of Computer Applications)", type=CourseType.UG, seats=60, fees=300000.0, eligibility_summary="Min 50% in 12th with Maths/Stats"),
    ]
    db.add_all(courses)
    db.commit()
    print("Seeded 4 default courses successfully.")

if __name__ == "__main__":
    seed()
