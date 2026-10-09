// Loaded into KWin by StreamController (src/backend/WindowGrabber/Integrations/KDE.py).
// Reports the active window to StreamController's DBus API whenever another
// window gets activated or the active window changes its title, instead of
// StreamController polling kdotool several times a second.
//
// Terminals are left out of title tracking: shells and TUIs retitle constantly
// (spinners, running commands) and would flood the bus for no benefit.
var NO_TITLE_TRACKING = ["kitty", "konsole", "org.kde.konsole", "alacritty", "foot",
                         "org.wezfurlong.wezterm", "com.mitchellh.ghostty", "xterm"];

var current = null;
var lastSent = "";

function notify(w) {
    var key = String(w.resourceClass) + "\n" + String(w.caption);
    if (key === lastSent) return;
    lastSent = key;
    callDBus("com.core447.StreamController", "/com/core447/StreamController",
             "com.core447.StreamController", "NotifyForegroundWindow",
             String(w.caption), String(w.resourceClass));
}

function onCaptionChanged() {
    if (current) notify(current);
}

function onActivated(w) {
    if (current) {
        try { current.captionChanged.disconnect(onCaptionChanged); } catch (e) {}
    }
    current = (w && w.normalWindow) ? w : null;
    if (!current) return;
    notify(current);
    if (NO_TITLE_TRACKING.indexOf(String(current.resourceClass).toLowerCase()) < 0) {
        current.captionChanged.connect(onCaptionChanged);
    }
}

workspace.windowActivated.connect(onActivated);
if (workspace.activeWindow) onActivated(workspace.activeWindow);
