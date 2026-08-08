from ui_text import (
    media_display_name,
    media_type_label,
    phase_label,
    played_label,
    question_kind_label,
    sound_label,
    timer_label,
)


def test_internal_values_have_russian_display_labels_and_safe_fallbacks():
    assert phase_label("PRE_ROUND") == "Ожидание вращения"
    assert phase_label("UNKNOWN") == "Неизвестная фаза"
    assert question_kind_label("superblitz") == "суперблиц"
    assert question_kind_label("UNKNOWN") == "неизвестный тип вопроса"
    assert media_type_label("image") == "изображение"
    assert media_type_label("UNKNOWN") == "медиа"
    assert sound_label("sector13") == "13-й сектор"
    assert sound_label("UNKNOWN") == "неизвестный звук"


def test_runtime_values_are_formatted_without_python_or_protocol_tokens():
    assert media_display_name({"name": "picture.jpg", "type": "image"}) == "picture.jpg"
    assert media_display_name({"name": "", "type": "audio"}) == "аудио"
    assert played_label(True) == "сыгран"
    assert played_label(False) == "доступен"
    assert timer_label(60) == "60 с"
    assert timer_label(None) == "выключен"
