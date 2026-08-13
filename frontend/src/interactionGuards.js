export function requiresAnswerMediaConfirmation(media, phase) {
  return media?.section === 'answer'
    && (phase === 'QUESTION_READING' || phase === 'DISCUSSION');
}
