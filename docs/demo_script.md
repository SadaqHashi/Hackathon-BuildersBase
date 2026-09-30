# TrustLens demo video script

Target: **under 3:00** (voice-over is about 2:30 of speech, leaving room for pauses).
Two tracks per scene:
- **YOU DO**: what you click and show in the screen recording.
- **VOICE**: the exact line to paste into ElevenLabs (one clip per scene).
- **CHECK**: what must be visible on screen while that line plays.

Workflow: record the screen once, all scenes in a row, slowly. Generate the 9 voice clips in ElevenLabs. Line them up per scene in your video editor and trim the pauses in the screen recording to fit the voice.

---

## Before you hit record

1. `.env`: `DEMO_MODE=false`. Leave `GOOGLE_API_KEY` empty, so the answer text is exactly as in this script (with a key, Gemini adds an extra sentence).
2. **Restart the backend** right before recording. Verifications and login attempts live in memory, and a restart gives a clean state.
3. Start the frontend, open http://localhost:8501, and **sign out** if a user is still signed in.
4. Browser: full screen (F11), zoom 110 to 125% so the text is readable in the video, one tab only, no bookmarks bar, notifications off.
5. Do one full dry run without recording, then restart the backend again (the dry run's verification would otherwise already show).
6. Move the mouse slowly. After every click, wait about 1 second before moving on.

---

## Scene 1: The problem (about 0:00 to 0:15)

**YOU DO**
- Start on the sign-in screen. Don't click anything yet. Slowly move the mouse over the title "TrustLens" and the tagline.

**VOICE**
> Payroll consultants find answers everywhere: policies, client files, emails, wikis, chats. The hard part isn't finding something. It's knowing whether you can rely on it. This is TrustLens.

**CHECK**: title and tagline "Find an answer, and see exactly why you can (or can't) rely on it."

---

## Scene 2: Jonas asks (about 0:15 to 0:27)

**YOU DO**
1. In the sidebar, type username `jonas`, password `hackathon`, click **Sign in**.
2. The question box already shows "What's the payroll input cutoff for Brouwerij Delvaux?". Click **Ask**.

**VOICE**
> Meet Jonas, a payroll consultant. His client, Brouwerij Delvaux, needs its payroll processed, and Jonas wants to know the input cutoff. So he asks.

**CHECK**: sidebar says "Jonas Peeters (consultant)", answer appears.

---

## Scene 3: The answer (about 0:27 to 0:45)

**YOU DO**
- Hover slowly over the answer headline, then the sentence under it, then "Uncertainty: Low", then "Not sure? Ask Sofie Maes".

**VOICE**
> TrustLens answers: the seventh working day. And it says why. Delvaux has an enterprise agreement that overrides the general Belgian rule, the fifth. Uncertainty is low, because three independent owners agree. And if Jonas still has doubts, it tells him exactly who to ask.

**CHECK**: "The 7th working day for Brouwerij Delvaux.", "Uncertainty: Low", "Not sure? Ask Sofie Maes (Payroll Compliance Lead BE)".

---

## Scene 4: Conflicts are shown, not hidden (about 0:45 to 0:57)

**YOU DO**
1. Hover over the three pills: "3 safe to rely on", "1 check before using", "5 don't rely on".
2. Click **"Sources disagree on 2 points. See who says what"** to open it. Hover over the rows 5th, 8th, 10th.
3. Click it again to close it.

**VOICE**
> But TrustLens doesn't hide what it left out. The sources disagree on two points, and you can see exactly who says the fifth, the eighth, and even the tenth.

**CHECK**: the conflict list with 5th / 8th / 10th and 6th / 7th.

---

## Scene 5: Green, and the five signals (about 0:57 to 1:17)

**YOU DO**
1. The green group **"Safe to rely on (3)"** is already open. Hover over the first card, "Client file - Brouwerij Delvaux".
2. Click **Show details** on that card. Hover down the five rows: Up to date, Owner, Kind of source, Applies to you, Backed by others.

**VOICE**
> Every source is sorted like a traffic light. Green is safe to rely on. Open any source and you see why: how recent it is, who owns it, what kind of source it is, whether it applies to this client, and whether other sources back it up. No black box. Five signals anyone can check.

**CHECK**: the five signal rows with coloured dots, and the quoted source text.

---

## Scene 6: The trap, newest is not right (about 1:17 to 1:40)

**YOU DO**
1. Scroll down. Click **"Don't rely on (5)"** to open the red group.
2. Find the card **"Teams #payroll-be"** by **Lars Wouters, 2026-08-20** (the one that says the 10th). Hover over its "why" line.
3. Click **Show details** on that card. Hover over "Up to date" (green dot), then "Backed by others" (red dot).

**VOICE**
> Red is where the traps are. This Teams chat is the newest source of all, and it claims the cutoff is now the tenth. A system that trusts the newest answer gets this wrong. TrustLens sees that nobody backs this claim, and that the official policy and a compliance email contradict it. So it's not relied on.

**CHECK**: "Says the 10th, but: No source backs the 10th; contradicted by ...". In details: green dot on Up to date, red dot on Backed by others. This contrast is the key moment of the video, so give it 2 to 3 seconds.

---

## Scene 7: The other traps (about 1:40 to 1:50)

**YOU DO**
- Slowly scroll through the other red cards: Client file Delvaux (2024), Policy v2, Policy Netherlands, Cutoff dates cheat sheet. Pause briefly on each "why" line.

**VOICE**
> The same goes for an outdated policy, an old client file, a wiki page nobody owns, and a Dutch policy that doesn't apply in Belgium.

**CHECK**: "Superseded by ...", "Applies to NL, not BE", "No source backs the 8th ...".

---

## Scene 8: Access control (about 1:50 to 2:02)

**YOU DO**
1. Scroll back up. Open the question dropdown, pick **"What's the payroll input cutoff for Garage Vermeulen?"**, click **Ask**.
2. Scroll through the source groups (open orange and red if needed). There is **no** "Client file - Garage Vermeulen".

**VOICE**
> Trust also means only seeing what you should. Garage Vermeulen is a colleague's client. When Jonas asks about it, its client file never leaves the server.

**CHECK**: no card titled "Client file - Garage Vermeulen" anywhere.

---

## Scene 9: The expert closes the loop (about 2:02 to 2:22)

**YOU DO**
1. Click **Sign out**. Sign in as `sofie` / `hackathon`.
2. Pick the Delvaux question again (first in the dropdown), click **Ask**.
3. In the green group, under **"Client file - Brouwerij Delvaux"**, click **Verify**. Wait for the badge "Verified by expert (sofie)".
4. Under **"Cutoff policy update"** (her own email, third green card), click **Verify**. The message "Cannot verify your own source" appears.

**VOICE**
> Experts close the loop. Sofie, the compliance lead, confirms the Delvaux client file, and every consultant now sees that an expert verified it. But she can't verify her own email. That rule is enforced on the server, not in the screen.

**CHECK**: green badge "Verified by expert (sofie)", then the red message "Cannot verify your own source".

---

## Scene 10: Closing (about 2:22 to 2:40)

**YOU DO**
- Scroll back to the top so the answer card is visible. Stop moving the mouse. Let it sit until the voice ends, then cut.

**VOICE**
> Under the hood, trust is computed by code, from each document's metadata, the same way every time. AI can explain an answer, but it never decides what to trust. TrustLens. Find it. Understand it. Trust it.

**CHECK**: the answer card on screen at the end.

---

## If you run over 3:00

Cut in this order: Scene 7 (other traps), then Scene 4 step 1 (the pills), then shorten Scene 8 to just the ask plus one scroll.

---

## ElevenLabs

**Settings to start with**: a calm, clear narrator voice, Stability about 50%, Similarity about 75%, Style 0%. Generate each scene as its own clip, so you can re-do one line without redoing everything.

**Pronunciation**: if a name comes out wrong, replace it in the text *for ElevenLabs only* with the respelling:

| Name | Say it like | Respelling to try |
|---|---|---|
| Brouwerij Delvaux | BROW-uh-ray del-VOH | Brow-ah-ray Del-voe |
| Garage Vermeulen | ga-RAHZH ver-MEU-len | Garage Ver-mur-len |
| Sofie | so-FEE | So-fee |

**Paste list** (one clip each):

1. Payroll consultants find answers everywhere: policies, client files, emails, wikis, chats. The hard part isn't finding something. It's knowing whether you can rely on it. This is TrustLens.
2. Meet Jonas, a payroll consultant. His client, Brouwerij Delvaux, needs its payroll processed, and Jonas wants to know the input cutoff. So he asks.
3. TrustLens answers: the seventh working day. And it says why. Delvaux has an enterprise agreement that overrides the general Belgian rule, the fifth. Uncertainty is low, because three independent owners agree. And if Jonas still has doubts, it tells him exactly who to ask.
4. But TrustLens doesn't hide what it left out. The sources disagree on two points, and you can see exactly who says the fifth, the eighth, and even the tenth.
5. Every source is sorted like a traffic light. Green is safe to rely on. Open any source and you see why: how recent it is, who owns it, what kind of source it is, whether it applies to this client, and whether other sources back it up. No black box. Five signals anyone can check.
6. Red is where the traps are. This Teams chat is the newest source of all, and it claims the cutoff is now the tenth. A system that trusts the newest answer gets this wrong. TrustLens sees that nobody backs this claim, and that the official policy and a compliance email contradict it. So it's not relied on.
7. The same goes for an outdated policy, an old client file, a wiki page nobody owns, and a Dutch policy that doesn't apply in Belgium.
8. Trust also means only seeing what you should. Garage Vermeulen is a colleague's client. When Jonas asks about it, its client file never leaves the server.
9. Experts close the loop. Sofie, the compliance lead, confirms the Delvaux client file, and every consultant now sees that an expert verified it. But she can't verify her own email. That rule is enforced on the server, not in the screen.
10. Under the hood, trust is computed by code, from each document's metadata, the same way every time. AI can explain an answer, but it never decides what to trust. TrustLens. Find it. Understand it. Trust it.
