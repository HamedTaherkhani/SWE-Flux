import importlib
import sys
import types


def install_wayland_backend_stubs() -> None:
    # pywayland
    pywayland_mod = types.ModuleType("pywayland")
    protocol_mod = types.ModuleType("pywayland.protocol")
    wayland_proto_mod = types.ModuleType("pywayland.protocol.wayland")
    server_mod = types.ModuleType("pywayland.server")

    class _KeyState:
        pressed = 1
        released = 0

    class WlKeyboard:
        key_state = _KeyState()

    class Listener:
        def __init__(self, *_args, **_kwargs):
            self._signal = types.SimpleNamespace(_ptr=object())

        def remove(self):
            return None

    class Client:
        @staticmethod
        def from_resource(_resource):
            return object()

    wayland_proto_mod.WlKeyboard = WlKeyboard
    server_mod.Listener = Listener
    server_mod.Client = Client

    protocol_mod.wayland = wayland_proto_mod
    pywayland_mod.protocol = protocol_mod
    pywayland_mod.server = server_mod

    sys.modules["pywayland"] = pywayland_mod
    sys.modules["pywayland.protocol"] = protocol_mod
    sys.modules["pywayland.protocol.wayland"] = wayland_proto_mod
    sys.modules["pywayland.server"] = server_mod

    # xkbcommon
    xkbcommon_mod = types.ModuleType("xkbcommon")
    xkb_mod = types.ModuleType("xkbcommon.xkb")

    class Context:
        def keymap_new_from_names(self, **_kwargs):
            return types.SimpleNamespace(state_new=lambda: object())

    xkb_mod.Context = Context
    xkbcommon_mod.xkb = xkb_mod
    sys.modules["xkbcommon"] = xkbcommon_mod
    sys.modules["xkbcommon.xkb"] = xkb_mod

    # wlroots
    wlroots_mod = types.ModuleType("wlroots")

    class PtrHasData:
        pass

    wlroots_mod.PtrHasData = PtrHasData
    sys.modules["wlroots"] = wlroots_mod

    util_box_mod = types.ModuleType("wlroots.util.box")

    class Box:
        def __init__(self, x=0, y=0, width=0, height=0):
            self.x = x
            self.y = y
            self.width = width
            self.height = height

    util_box_mod.Box = Box
    sys.modules["wlroots.util.box"] = util_box_mod

    wlr_types_mod = types.ModuleType("wlroots.wlr_types")

    class Buffer:
        pass

    wlr_types_mod.Buffer = Buffer
    sys.modules["wlroots.wlr_types"] = wlr_types_mod

    idle_mod = types.ModuleType("wlroots.wlr_types.idle_inhibit_v1")

    class IdleInhibitorV1:
        pass

    idle_mod.IdleInhibitorV1 = IdleInhibitorV1
    sys.modules["wlroots.wlr_types.idle_inhibit_v1"] = idle_mod

    pc_mod = types.ModuleType("wlroots.wlr_types.pointer_constraints_v1")

    class PointerConstraintV1:
        pass

    class PointerConstraintV1StateField:
        pass

    pc_mod.PointerConstraintV1 = PointerConstraintV1
    pc_mod.PointerConstraintV1StateField = PointerConstraintV1StateField
    sys.modules["wlroots.wlr_types.pointer_constraints_v1"] = pc_mod

    scene_mod = types.ModuleType("wlroots.wlr_types.scene")

    class DummyNode:
        def __init__(self):
            self.enabled = True

        def set_enabled(self, enabled=True):
            self.enabled = enabled

        def set_position(self, _x, _y):
            return None

        def destroy(self):
            return None

        def raise_to_top(self):
            return None

        def subsurface_tree_set_clip(self, _box):
            return None

    class SceneTree:
        @staticmethod
        def create(_parent):
            return types.SimpleNamespace(node=DummyNode(), children=iter([object()]))

    class SceneRect:
        def __init__(self, _container, _w, _h, _color):
            self.node = DummyNode()

        def set_color(self, _color):
            return None

        def set_size(self, _w, _h):
            return None

    class SceneBuffer:
        pass

    scene_mod.SceneTree = SceneTree
    scene_mod.SceneRect = SceneRect
    scene_mod.SceneBuffer = SceneBuffer
    scene_mod.DummyNode = DummyNode
    sys.modules["wlroots.wlr_types.scene"] = scene_mod

    ftm_mod = types.ModuleType("wlroots.wlr_types.foreign_toplevel_management_v1")

    class ForeignToplevelHandleV1:
        pass

    class ForeignToplevelHandleV1MaximizedEvent:
        pass

    class ForeignToplevelHandleV1MinimizedEvent:
        pass

    class ForeignToplevelHandleV1FullscreenEvent:
        pass

    class ForeignToplevelHandleV1ActivatedEvent:
        pass

    ftm_mod.ForeignToplevelHandleV1 = ForeignToplevelHandleV1
    ftm_mod.ForeignToplevelHandleV1MaximizedEvent = ForeignToplevelHandleV1MaximizedEvent
    ftm_mod.ForeignToplevelHandleV1MinimizedEvent = ForeignToplevelHandleV1MinimizedEvent
    ftm_mod.ForeignToplevelHandleV1FullscreenEvent = ForeignToplevelHandleV1FullscreenEvent
    ftm_mod.ForeignToplevelHandleV1ActivatedEvent = ForeignToplevelHandleV1ActivatedEvent
    sys.modules["wlroots.wlr_types.foreign_toplevel_management_v1"] = ftm_mod

    # wayland helper modules
    wayland_drawer_mod = types.ModuleType("libqtile.backend.wayland.drawer")

    class Drawer:
        pass

    wayland_drawer_mod.Drawer = Drawer
    sys.modules["libqtile.backend.wayland.drawer"] = wayland_drawer_mod

    wayland_wlrq_mod = types.ModuleType("libqtile.backend.wayland.wlrq")

    class HasListeners:
        def add_listener(self, *_args, **_kwargs):
            return None

        def finalize_listeners(self):
            return None

    wayland_wlrq_mod.HasListeners = HasListeners
    wayland_wlrq_mod.buttons = [0x110, 0x111, 0x112]
    sys.modules["libqtile.backend.wayland.wlrq"] = wayland_wlrq_mod

    # wayland ffi shim
    ffi_mod = types.ModuleType("libqtile.backend.wayland._ffi")

    class DummyFFI:
        class CData(list):
            pass

        def new(self, _ctype, value=None):
            if value is None:
                value = [0]
            if isinstance(value, tuple):
                value = list(value)
            if not isinstance(value, list):
                value = [value]
            return DummyFFI.CData(value)

        def new_handle(self, obj):
            return obj

    ffi_mod.ffi = DummyFFI()
    ffi_mod.lib = types.SimpleNamespace(
        LIBINPUT_CONFIG_ACCEL_PROFILE_ADAPTIVE=1,
        LIBINPUT_CONFIG_ACCEL_PROFILE_FLAT=2,
        LIBINPUT_CONFIG_CLICK_METHOD_NONE=10,
        LIBINPUT_CONFIG_CLICK_METHOD_BUTTON_AREAS=11,
        LIBINPUT_CONFIG_CLICK_METHOD_CLICKFINGER=12,
        LIBINPUT_CONFIG_TAP_MAP_LRM=20,
        LIBINPUT_CONFIG_TAP_MAP_LMR=21,
        LIBINPUT_CONFIG_SCROLL_NO_SCROLL=30,
        LIBINPUT_CONFIG_SCROLL_2FG=31,
        LIBINPUT_CONFIG_SCROLL_EDGE=32,
        LIBINPUT_CONFIG_SCROLL_ON_BUTTON_DOWN=33,
    )
    sys.modules["libqtile.backend.wayland._ffi"] = ffi_mod


install_wayland_backend_stubs()
inputs_mod = importlib.import_module("libqtile.backend.wayland.inputs")
window_mod = importlib.import_module("libqtile.backend.wayland.window")


class DummyTimer:
    def __init__(self, tag: int):
        self.tag = tag
        self.cancelled = False

    def cancel(self):
        self.cancelled = True


class DummyScreen:
    def __init__(self):
        self.x = 19
        self.y = 11
        self.index = 0
        self.group = None


class DummyGroup:
    def __init__(self, screen: DummyScreen):
        self.screen = screen
        self.mark_floating_calls = 0

    def mark_floating(self, _win, _flag):
        self.mark_floating_calls += 1

    def remove(self, *_args, **_kwargs):
        return None

    def add(self, *_args, **_kwargs):
        return None


class DummyWindowChainProbe:
    move_floating = window_mod.Window.move_floating
    _tweak_float = window_mod.Window._tweak_float
    _reconfigure_floating = window_mod.Window._reconfigure_floating
    paint_borders = window_mod.Window.paint_borders

    def __init__(self):
        self.x = 121
        self.y = 77
        self._width = 540
        self._height = 330
        self.width = self._width
        self.height = self._height

        self._float_state = window_mod.FloatStates.NOT_FLOATING
        self._opacity = 1.0

        self.borderwidth = 3
        self.bordercolor = ["334455", "667788", "99aabb"]
        self._borders = []

        dummy_node_cls = sys.modules["wlroots.wlr_types.scene"].DummyNode
        self.container = types.SimpleNamespace(node=dummy_node_cls())
        self.tree = types.SimpleNamespace(node=dummy_node_cls(), children=iter([object()]))

        screen = DummyScreen()
        self.group = DummyGroup(screen)
        screen.group = self.group

        self.qtile = None
        self._fullscreen_updates = []

    def _update_fullscreen(self, do_full: bool) -> None:
        self._fullscreen_updates.append(do_full)

    def place(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        borderwidth: int,
        bordercolor,
        above: bool = False,
        margin=None,
        respect_hints: bool = False,
    ) -> None:
        if margin is not None:
            if isinstance(margin, int):
                margin = [margin] * 4
            x += margin[3]
            y += margin[0]
            width -= margin[1] + margin[3]
            height -= margin[0] + margin[2]

        if respect_hints:
            width = max(width, 120)
            height = max(height, 90)

        self.x = x
        self.y = y
        self._width = max(1, width)
        self._height = max(1, height)
        self.width = self._width
        self.height = self._height

        self.paint_borders(bordercolor, borderwidth)

        if above:
            self.container.node.raise_to_top()

    def hide(self) -> None:
        return None


class DummyQtile:
    def __init__(self, window_probe: DummyWindowChainProbe):
        self.window_probe = window_probe
        self.scheduled = 0
        self.recursion_budget = sum((i % 3) + 1 for i in range(1, 10))
        self.process_calls = []
        self.focus_screen_calls = 0

    def call_later(self, _delay, callback, *args):
        self.scheduled += 1
        timer = DummyTimer(self.scheduled)
        if self.scheduled < self.recursion_budget:
            callback(*args)
        return timer

    def process_key_event(self, keysym, mods):
        self.process_calls.append((keysym, mods))

        dx = (keysym % 5) - 2
        dy = (len(self.process_calls) % 7) - 3
        self.window_probe.move_floating(dx, dy)

        handled = (len(self.process_calls) % 23 == 0) and (keysym % 2 == 0)
        return None, handled

    def find_closest_screen(self, _x, _y):
        return self.window_probe.group.screen

    def focus_screen(self, _index):
        self.focus_screen_calls += 1


class DummyKeyboardRepeatProbe:
    _on_repeat_key = inputs_mod.Keyboard._on_repeat_key

    def __init__(self):
        self.keyboard = types.SimpleNamespace(
            _ptr=types.SimpleNamespace(repeat_info=types.SimpleNamespace(rate=35))
        )
        self.repeat_delay_future = object()
        self.repeat_rate_future = None

        self.window_probe = DummyWindowChainProbe()
        self.qtile = DummyQtile(self.window_probe)
        self.window_probe.qtile = self.qtile

        self.grabbed_keys = {(31, 9), (47, 9), (59, 9), (67, 9), (71, 9)}


class TestBackendWaylandInputsDirectRepeatKeyMaxCallDepthQA:
    def test_backend_wayland_inputs_direct_repeat_key_max_call_depth_case(self):
        probe = DummyKeyboardRepeatProbe()

        # One direct entry call, with eager recursive scheduling and chained window logic.
        probe._on_repeat_key([31, 47, 59, 61, 67, 71], 9)

        assert probe.qtile.scheduled == probe.qtile.recursion_budget
        assert probe.qtile.scheduled > 12
        assert probe.repeat_rate_future is not None

        assert len(probe.qtile.process_calls) > 40
        assert all(mods == 9 for _, mods in probe.qtile.process_calls)

        assert probe.window_probe.group.mark_floating_calls >= 1
        assert probe.window_probe._float_state == window_mod.FloatStates.FLOATING
        assert len(probe.window_probe._borders) == 3
