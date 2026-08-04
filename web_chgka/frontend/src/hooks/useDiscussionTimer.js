import { useCallback, useEffect, useRef, useState } from 'react';

export function useDiscussionTimer({ isAdmin, isDiscussion, deadlineMs, addNotification, playSound }) {
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
      if (!deadlineMs) {
        setRemaining(null);
        return;
      }

      const raw = (deadlineMs - Date.now()) / 1000;
      const nextRemaining = raw >= 0 ? Math.ceil(raw) : Math.floor(raw);
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
  }, [deadlineMs, isAdmin, isDiscussion]);

  return { discussionRemaining: remaining, markTenSecondsNotified };
}
