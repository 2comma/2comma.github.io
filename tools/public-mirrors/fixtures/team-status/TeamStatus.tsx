import { Page, Section, Rows, Table, Callout, Text } from "grok/canvas";

export default function App() {
  return (
    <Page title="Team Status" summary="What needs you, what's blocked, and what each bot is doing, highest priority first. Updated daily at 7 AM PT. As of Thu Nov 5, 2026, 7:00 AM PT." width="wide">
      <Section heading="Needs you">
        <Rows rows={[
          { lead: "1", title: "Check that Tobi's paused routines are back on", detail: "At 10:58 PM last night Tobi's scheduled resume was refused (a routine run can't re-enable routines), so it asked for these to be resumed from chat: the 8 AM morning brief, the wishlist price tracker, the iPhone Duo instant-buy, the Lems order tracking and the watcher health check. The health check has logged every hour since midnight, but no log line shows the other four were turned back on. Today's 8 AM brief and the iPhone auto-buy (watch ends Nov 8) depend on them.", meta: "Tobi", status: { label: "Before 8 AM", tone: "danger" } },
          { lead: "2", title: "Approve dr eggbot creating the pilot's watchdog and Nov 12 routines", detail: "The no-AI page-check pilot for Zen started at 4 AM: the script is built, tested and running, and the design went to Zen. The watchdog and the Nov 12 follow-up routines couldn't be created from a routine run, so they need a go-ahead in dr eggbot's chat.", meta: "dr eggbot", status: { label: "Blocking pilot", tone: "warning" } },
          { lead: "3", title: "Confirm the Lems order arrived", detail: "the UPS shipment was expected Wed Nov 4. Tobi deletes the tracking routine only after you confirm delivery.", meta: "Tobi", status: { label: "Awaiting you" } },
          { lead: "4", title: "Pick Levi's ideas for Zen", detail: "Carried over. My recommendation was the beehiiv connector only, skipping the separate-email routines. Levi also sent one keeper on Nov 2 (a PropRuleWatch sponsor slot). Nothing on the board or in the logs shows a decision yet.", meta: "Gojo", status: { label: "Awaiting you" } },
          { lead: "5", title: "Give L the go for the next stocks-course batch", detail: "Lessons 73 to 77 are recorded (77 of 163). L is paused until you say to start the next batch at lesson 78.", meta: "L", status: { label: "Optional" } },
          { lead: "6", title: "Website category expansion", detail: "Morgans ranked the options with Personal Finance first; the ranking is in Morgans' chat.", meta: "Morgans", status: { label: "Optional" } }
        ]} />
        <Text>Cleared since the last update: the NY Life cancellation (Tobi logged that you submitted termination for the policy on Nov 2; the BofA check on Nov 17 stays) and Ace's course block (you said resume, and Ace is recording again).</Text>
      </Section>
      <Section heading="Blocked">
        <Rows rows={[
          { title: "Routinizer pilot follow-up routines", detail: "Watchdog and Nov 12 routines not created; waiting on item 2 above. The existing Zen page check stays on until the pilot is verified.", meta: "dr eggbot", status: { label: "Blocked", tone: "warning" } },
          { title: "Short-form video", detail: "On hold by you until an easier option appears.", meta: "Morgans", status: { label: "On hold" } }
        ]} />
      </Section>
      <Section heading="Each bot">
        <Table columns={["Bot", "Working on", "Latest result", "Last log (PT)"]} rows={[
          ["Zen (was Jack)", "TwoComma News site, TwoComma Trade site, YNWA hub, TwoComma Read, PropRuleWatch, 1892 Reds LFC site", "Nov 2 afternoon: TwoComma Read updated (HPMOR ch01 v9, RR ch01 v2) with the password gate verified, and the Nov 2 PM news digest deployed. Monday review that day found Beehiiv signed out. Nothing logged since, including the Nov 4 and Nov 5 briefs Morgans sent.", "Nov 2, 2:19 PM"],
          ["Morgans", "TwoComma News briefs and Buffer drafts", "This morning's Asia (5 items), World (4, after one retry from chat when the routine was interrupted) and crypto and markets (5) briefs all passed checks. Routines resumed after the pause; the old separate Entertainment, US and Politics routines were deleted at your request.", "Nov 5, 5:28 AM"],
          ["Tobi", "Weekday 8 AM brief, price tracker, iPhone watcher, Lems order, subscription follow-ups", "The iPhone watcher died at 2:03 AM, was restarted at 3:55 AM and has been healthy since (latest 5:59 AM, no stock). Resume of its other paused routines needed chat (item 1).", "Nov 5, 5:59 AM"],
          ["L (was Reo)", "Daily trade brief, stocks course study, calibration log", "Stocks course lessons 73 to 77 recorded overnight, paused for your go. Nov 4: trade brief all FLAT and validated; GPS tracker unchanged after the CryptoCrew re-sign-in.", "Nov 5, 1:31 AM"],
          ["Ace (was Conan)", "Legal research; real estate course study", "Resumed at 16.4 on your go and has recorded through 20.8; transcribing, next section started.", "Nov 5, 4:51 AM"],
          ["Boa", "Graphics; comic-craft lessons for the book-to-manga skill", "Delivered the high-quality Team TwoComma logo (Zen put it on YNWA Nov 2). Paused the One Piece study for 48 hours on Nov 2, due back Nov 4 at 10:55 PM; no log line on the resume.", "Nov 1, 12:50 PM"],
          ["Levi", "Daily income-improvement scan", "Scan resumed Nov 4 after the pause. Last scan (Nov 2) sent one keeper, a PropRuleWatch sponsor slot, to Gojo.", "Nov 4, 11:01 PM"],
          ["dr eggbot", "Bot design, health checks, routinizer pilot", "Pilot baseline saved (0 page-check wakes in the last 7 days); page-check script built, tested and running; design sent to Zen. Correction review and routine health check resumed by you Nov 4.", "Nov 5, 4:07 AM"],
          ["Klopp", "1892 Reds LFC site data, your 14-point revamp", "Daily and weekly routines resumed Nov 4. Last results: Nov 2 news and fixtures, with the Carabao Cup quarterfinal against Bournemouth added (date to be confirmed).", "Nov 4, 10:56 PM"]
        ]} />
      </Section>
      <Section heading="Rules check">
        <Callout tone="warning">Sixteen open board rows are more than 2 days old. Tobi: price tracker, morning brief, NY Life (still says awaiting approval though it's done), creator sub, iPhone watch, Lems order, BofA check. Zen: PropRuleWatch Monday review, template ideas, TwoComma News site. L: FOMC dates (the event_stress.py edit is still marked NEEDS REVIEW) and calibration log. Morgans: TwoComma News brief, TwoComma News site, short video. Shared: the 1892 Reds LFC site (Oct 28).</Callout>
        <Text>Missing logs for rolled-out changes: Zen has no log line for the Nov 2 to 4 pause or anything after Nov 2, 2:19 PM, and Boa logged neither the pause nor the resume (only a board bullet). Board format: the routinizer row uses a status (scheduled) that isn't on the list, Zen's two GitHub rows are still missing columns and dates, and Ace's and Boa's items are bullets under the table instead of rows. Log format: Ace's lines use UTC times, L's recent lines and Morgans' Nov 3 and 4 lines aren't in the five-field format, and Levi's Nov 4 resume line has no time.</Text>
      </Section>
    </Page>
  );
}
