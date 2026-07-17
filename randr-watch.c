#include <X11/Xlib.h>
#include <X11/extensions/Xrandr.h>

int main() {
	Display *display = XOpenDisplay(NULL);
	if (!display) return 1;

	int event_base, error_base;
	if (!XRRQueryExtension(display, &event_base, &error_base)) return 1;

	XRRSelectInput(display, DefaultRootWindow(display), RRScreenChangeNotifyMask);

	XEvent evt;
	for (;;) {
		XNextEvent(display, &evt);
		if (evt.type == event_base + RRScreenChangeNotify)
			return 0;
	}
}
