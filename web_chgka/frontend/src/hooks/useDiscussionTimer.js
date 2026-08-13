import { useCallback, useEffect, useRef, useState } from 'react';
import { timerRemainingSeconds } from '../gameMinutes';

export function useDiscussionTimer({ isAdmin, isDiscussion, timer, addNotification, playSound }) {
  const [remaining, setRemaining] = useState(null);
  const tenSecNotifiedRef = useRef(false);
  const lastRemainingRef = useRef(null);
  const addNotificationRef = useRef(addNotification);
  const playSoundRef = useRef(playSound);

  useEffect(() => {
    addNotificationRef.current = addNotification;
    playSoundRef.current = playSound;
  }, [addNotification, playSound]);

  const markTenSecondsNotified = useCallback(() => {
    tenSecNotifiedRef.current = true;
  }, []);

  useEffect(() => {
    if (!isAdmin) return;
    if (!isDiscussion) {
      setRemaining(null);
      tenSecNotifiedRef.current = false;
      lastRemainingRef.current = null;
      return;
    }

    tenSecNotifiedRef.current = false;
    lastRemainingRef.current = null;

    const tick = () => {
      if (!timer?.discussion_deadline_ms) {
        setRemaining(null);
        return;
      }

      const nextRemaining = timerRemainingSeconds(timer);
      setRemaining(nextRemaining);

      const previousRemaining = lastRemainingRef.current;
      lastRemainingRef.current = nextRemaining;

      if (
        !tenSecNotifiedRef.current
        && previousRemaining !== null
        && previousRemaining > 10
        && nextRemaining <= 10
      ) {
        tenSecNotifiedRef.current = true;
        addNotificationRef.current({ type: 'warning', message: 'Осталось 10 секунд' });
        playSoundRef.current('sig2');
      }
    };

    tick();
    const interval = setInterval(tick, 250);
    return () => clearInterval(interval);
  }, [isAdmin, isDiscussion, timer]);

  return { discussionRemaining: remaining, markTenSecondsNotified };
}
