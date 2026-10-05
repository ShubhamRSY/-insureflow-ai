import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { SplitText } from 'gsap/SplitText';
import { useGSAP } from '@gsap/react';

gsap.registerPlugin(useGSAP, SplitText);
// ScrollTrigger calls matchMedia as it registers; jsdom has none (motion is off there anyway).
if (typeof window !== 'undefined' && window.matchMedia) gsap.registerPlugin(ScrollTrigger);

export { gsap, ScrollTrigger, SplitText, useGSAP };

const MOTION_OK = '(prefers-reduced-motion: no-preference)';

// Animations only run for users who haven't asked for reduced motion (and
// never in jsdom, which has no matchMedia). Content is visible by default, so
// skipping the animation never hides anything.
export function motionAllowed() {
  return typeof window !== 'undefined' && !!window.matchMedia && window.matchMedia(MOTION_OK).matches;
}

// Like motionAllowed, but re-runs/reverts `fn` if the preference changes.
export function withMotion(fn) {
  if (typeof window === 'undefined' || !window.matchMedia) return;
  gsap.matchMedia().add(MOTION_OK, fn);
}
