

def get_question_answer_for_quiz():
    with open('questions/1vs1200.txt', 'r', encoding='KOI8-R') as file:
        content = file.read()

    sections = content.split('\n\n')
    quiz_game = {}

    for i, section in enumerate(sections):
        if section.startswith('Вопрос'):
            _, question_text = section.split(':', 1)
            if i + 1 < len(sections) and sections[i + 1].startswith('Ответ:'):
                _, answer_text = sections[i + 1].split(':', 1)
                quiz_game[question_text.strip()] = answer_text.strip()

    return quiz_game


def check_answer(user_answer, correct_answer):
    correct_answer = correct_answer.lower().strip()
    if '.' in correct_answer:
        correct_answer = correct_answer.split('.')[0]
    if '(' in correct_answer:
        correct_answer = correct_answer.split('(')[0]

    return user_answer.lower().strip() == correct_answer
