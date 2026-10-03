"""Offline regressions for presentation terminal tabs and keyboard shortcuts."""

from html.parser import HTMLParser
from pathlib import Path
import shlex
import subprocess
import unittest

import yaml

ROOT = Path(__file__).resolve().parent.parent


class CodeExample(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_pre = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "pre":
            self.in_pre = True

    def handle_endtag(self, tag):
        if tag == "pre":
            self.in_pre = False

    def handle_data(self, data):
        if self.in_pre:
            self.parts.append(data)


class DemoItTests(unittest.TestCase):
    def permissions_slide(self):
        slides = (ROOT / "demoit.html").read_text().split("\n---\n")
        index = next(i for i, slide in enumerate(slides)
                     if "<h1>Tool call permissions</h1>" in slide)
        return slides[index], slides[index + 1]

    def test_permissions_slide_is_optional_and_has_no_live_side_effects(self):
        slide, following = self.permissions_slide()
        self.assertNotIn("Optional 1/5 · 4 min", slide)
        self.assertIn('class="optional-marker"', slide)
        self.assertIn('aria-label="Optional slide"', slide)
        self.assertIn("<speaker-notes>", slide)
        for step in ["Look up facts", "Practice a match"]:
            self.assertIn(step, slide)
        self.assertIn("skip straight to structured output", slide)
        self.assertIn("<h1>Give software a predictable answer</h1>", following)
        slides = (ROOT / "demoit.html").read_text().split("\n---\n")
        index = slides.index(slide)
        self.assertIn("<h1>Give the agent the same API call</h1>", slides[index - 1])
        self.assertIn('<span class="stage">02</span>Connect', slide)
        self.assertNotIn("join_local_arena", slide)
        self.assertNotIn("<web-term", slide)
        self.assertNotIn("<web-browser", slide)
        for boundary in ["DATA-1", "FAIR-1", "not a sandbox", "explicit user request",
                         "wins over", "can bypass YAML"]:
            self.assertIn(boundary, slide)

    def test_permissions_slide_keeps_explanation_brief(self):
        slide, _ = self.permissions_slide()
        visible = slide.split("<speaker-notes>")[0]
        self.assertIn('class="permission-flow"', visible)
        self.assertIn('class="command permission-example"', visible)
        self.assertIn('<p class="subtitle">Choose what runs and what needs approval</p>', visible)
        self.assertNotIn("In strict mode: run lookups and practice, confirm submissions.", visible)
        self.assertNotIn('class="permission-explanation"', visible)
        self.assertIn('class="slide-corner corner-small" src="/images/shield.svg"', visible)
        for clutter in ['class="caption"', 'class="takeaway"', 'class="two-columns"', '<h3>']:
            self.assertNotIn(clutter, visible)

    def test_displayed_permissions_use_only_introduced_tools(self):
        slide, _ = self.permissions_slide()
        example = CodeExample()
        example.feed(slide)
        excerpt = yaml.safe_load("".join(example.parts))
        self.assertEqual(excerpt, {
            "runtime": {"safety": "strict"},
            "permissions": {
                "allow": ["pokemon_retrieve"],
                "ask": ["spar_team"],
            },
        })
        live = yaml.safe_load((ROOT / "agents/10-sparring.yaml").read_text())
        fact_tools = live["agents"]["root"]["toolsets"][0]["tools"]
        api_tool = live["agents"]["root"]["toolsets"][1]["api_config"]["name"]
        self.assertTrue(set(excerpt["permissions"]["allow"]) <= set(fact_tools))
        self.assertEqual(excerpt["permissions"]["ask"], [api_tool])
        self.assertNotIn(api_tool, excerpt["permissions"]["allow"])
        self.assertIn("illustrative permissions excerpt", slide)
        self.assertIn("--safety strict", slide)
        self.assertNotIn("require-confirmation.sh", slide)

    def test_tracing_slide_is_optional_and_follows_application_demo(self):
        slides = (ROOT / "demoit.html").read_text().split("\n---\n")
        index = next(i for i, slide in enumerate(slides)
                     if "<h1>See the agent's trace</h1>" in slide)
        slide = slides[index]
        self.assertIn("<h1>Call the agent from an application</h1>", slides[index - 1])
        self.assertIn("<h1>An agent calls the builder as a tool</h1>", slides[index + 1])
        self.assertIn('class="optional-marker"', slide)
        self.assertIn("skip straight to MCP", slide)
        for limitation in ["before the talk", "omitted by default",
                           "need their own instrumentation", "DATA-1", "FAIR-1"]:
            self.assertIn(limitation, slide)
        self.assertIn('class="terminal-stack tracing-terminals"', slide)
        self.assertIn('<web-browser src="http://127.0.0.1:16686/search">', slide)
        self.assertIn("Find Traces", slide)
        class Commands(HTMLParser):
            def __init__(self):
                super().__init__()
                self.commands = []

            def handle_starttag(self, tag, attrs):
                if tag == "web-term":
                    self.commands.append(dict(attrs)["command"])

        terminals = Commands()
        terminals.feed(slide)
        viewer, server, client = terminals.commands
        self.assertEqual(shlex.split(viewer), ["python3", "scripts/trace_viewer.py"])
        self.assertEqual(shlex.split(server), [
            "OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318",
            "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=false",
            "docker", "agent", "serve", "chat", "agents/13-service.yaml",
            "--listen", "127.0.0.1:8082", "--otel",
        ])
        self.assertEqual(shlex.split(client), [
            "python3", "scripts/api_client.py", "--url", "http://127.0.0.1:8082",
        ])
        for path in ["README.md", ".demoit/.bash_history"]:
            text = (ROOT / path).read_text()
            for command in terminals.commands:
                self.assertIn(command, text)
        collector = yaml.safe_load((ROOT / "compose.tracing.yaml").read_text())
        service, = collector["services"].values()
        self.assertIn("@sha256:", service["image"])
        self.assertEqual(service["ports"], [
            "127.0.0.1:16686:16686", "127.0.0.1:4318:4318",
        ])

    def test_plus_button_opens_empty_terminal_without_changing_initial_command(self):
        result = subprocess.run(["node", "-e", r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const elements = new Map();
const terminals = [];
const observers = [];
class HTMLElement {
    attachShadow() {
        this.shadowRoot = {
            windows: [],
            set innerHTML(value) { this.windows = []; },
            activeElement: null,
            appendChild(window) {
                window.parentRoot = this;
                this.windows.push(window);
                return window;
            },
            querySelector(selector) {
                return selector === 'iframe' ? this.windows[0]?.frame : this.windows[0];
            },
        };
    }
    getAttribute(name) { return this.attributes[name] ?? null; }
}

const document = {
    querySelector() { return null; },
    querySelectorAll() { return terminals; },
    getElementsByTagName() { return []; },
    addEventListener() {},
    createElement() {
        return {
            set innerHTML(html) {
                const listeners = {};
                const shortcuts = {};
                this.frame = {
                    url: html.match(/src="([^"]+)"/)[1],
                    navigations: 0,
                    get src() { return this.url; },
                    set src(value) { this.url = value; this.navigations++; },
                    isConnected: true,
                    contentDocument: { getElementById() { return null; } },
                    contentWindow: {
                        focused: false,
                        addEventListener(name, listener, capture) {
                            assert.equal(capture, true);
                            shortcuts[name] = listener;
                        },
                        focus() {
                            this.focused = true;
                            frame.parentWindow.parentRoot.activeElement = frame;
                        },
                        keydown(event) { shortcuts.keydown(event); },
                    },
                    addEventListener(name, listener) { listeners[name] = listener; },
                    load() { listeners.load(); },
                };
                const frame = this.frame;
                const redListeners = {};
                const red = {
                    addEventListener(name, listener) { redListeners[name] = listener; },
                    click() { redListeners.click(); },
                    mousedown(event) { redListeners.mousedown(event); },
                };
                const plus = {
                    addEventListener(name, listener) { this.clickHandler = listener; },
                    click() {
                        let prevented = false;
                        this.clickHandler({ preventDefault() { prevented = true; } });
                        assert.equal(prevented, true);
                    },
                };
                this.lastChild = {
                    frame: this.frame,
                    plus,
                    red,
                    maximized: false,
                    remove() {
                        const windows = this.parentRoot.windows;
                        windows.splice(windows.indexOf(this), 1);
                        this.frame.isConnected = false;
                    },
                    querySelector() { return plus; },
                    $(selector) {
                        if (selector === '#red') {
                            return red;
                        }
                        if (selector === '#main') {
                            return { classList: { contains: () => this.maximized } };
                        }
                        assert.equal(selector, '#green');
                        return { click: () => { this.maximized = !this.maximized; } };
                    },
                };
                this.frame.parentWindow = this.lastChild;
            },
            querySelector() { return this.frame; },
        };
    },
};

vm.runInNewContext(fs.readFileSync('.demoit/js/demoit.js', 'utf8'), {
    document,
    HTMLElement,
    customElements: { define(name, element) { elements.set(name, element); } },
    BroadcastChannel: class { postMessage() {} },
    MutationObserver: class {
        constructor(callback) { this.callback = callback; observers.push(this); }
        observe() {}
        disconnect() { this.disconnected = true; }
    },
    CurrentStep: 1,
    StepCount: 1,
});

const WebTerm = elements.get('web-term');
for (const path of ['.', 'agents']) {
    for (const command of [null, '', 'docker agent run demo.yaml "hello & goodbye?"']) {
        const terminal = new WebTerm();
        terminal.attributes = { path, command };
        terminal.connectedCallback();
        terminal.shadowRoot.querySelectorAll = () => terminal.shadowRoot.windows;
        terminals.length = 0;
        terminals.push(terminal);
        const windows = terminal.shadowRoot.windows;
        const initial = windows[0].frame;
        const expected = `/shell/${path}` + (command ? `?command=${encodeURIComponent(command)}` : '');
        assert.equal(initial.src, expected);
        initial.load();
        assert.equal(initial.contentWindow.focused, false);

        for (let i = 0; i < 3; i++) {
            windows[i].plus.click();
            assert.equal(windows.length, i + 2);
            const added = windows[i + 1].frame;
            assert.equal(added.src, `/shell/${path}`);
            assert.equal(added.contentWindow.focused, false);
            added.load();
            assert.equal(added.contentWindow.focused, true);
            assert.equal(initial.src, expected);
            assert.equal(terminal.command, command);

            const event = {
                metaKey: true,
                key: 'Enter',
                preventDefault() { this.defaultPrevented = true; },
                stopPropagation() { this.stopped = true; },
            };
            added.contentWindow.keydown(event);
            assert.equal(windows[i + 1].maximized, true);
            assert.equal(windows[0].maximized, false);
            assert.equal(event.defaultPrevented, true);
            assert.equal(event.stopped, true);
            added.contentWindow.keydown(event);
            assert.equal(windows[i + 1].maximized, false);
            assert.equal(added.contentWindow.focused, true);

            windows[0].$('#green').click();
            added.contentWindow.keydown(event);
            assert.equal(windows[0].maximized, false);
            assert.equal(windows[i + 1].maximized, false);
        }

        // Reset only the initial shell, with its original command and size.
        const input = { focused: false, focus() { this.focused = true; } };
        initial.contentDocument.getElementById = () => ({ querySelector() { return input; } });
        initial.contentWindow.focus();
        const originalWindow = windows[0];
        let prevented = false;
        originalWindow.red.mousedown({ preventDefault() { prevented = true; } });
        assert.equal(prevented, true);
        originalWindow.$('#green').click();
        originalWindow.red.click();
        assert.equal(windows.length, 4);
        assert.equal(windows[0], originalWindow);
        assert.equal(initial.src, expected);
        assert.equal(initial.navigations, 1);
        assert.equal(originalWindow.maximized, true);
        assert.equal(terminal.pendingFocus, initial);
        initial.load();
        assert.equal(initial.contentWindow.focused, true);
        assert.equal(input.focused, true);
        assert.equal(terminal.pendingFocus, null);
        input.focused = false;
        originalWindow.red.click();
        initial.load();
        assert.equal(initial.navigations, 2);
        assert.equal(input.focused, true);

        // Closing an unfocused middle terminal must not move focus.
        const focused = windows[3].frame;
        terminal.shadowRoot.activeElement = focused;
        const middle = windows[2];
        middle.red.click();
        assert.equal(windows.length, 3);
        assert.equal(middle.frame.isConnected, false);
        assert.equal(terminal.shadowRoot.activeElement, focused);
        assert.equal(initial.navigations, 2);

        // Close the focused added terminal, including when maximized.
        windows[2].$('#green').click();
        windows[2].red.click();
        assert.equal(windows.length, 2);
        assert.equal(terminal.shadowRoot.activeElement, initial);
        windows[1].red.click();
        assert.equal(windows.length, 1);
        originalWindow.plus.click();
        assert.equal(windows[1].frame.src, `/shell/${path}`);

        // Closing before asynchronous terminal initialization cancels focus.
        const pending = windows[1];
        pending.frame.contentDocument.getElementById = () => ({ querySelector() { return null; } });
        pending.frame.load();
        const observer = observers.at(-1);
        assert.equal(terminal.pendingFocus, pending.frame);
        pending.red.click();
        assert.equal(observer.disconnected, true);
        assert.equal(terminal.pendingFocus, null);
        observer.callback();
        assert.equal(pending.frame.contentWindow.focused, false);
        assert.equal(windows.length, 1);
        assert.equal(terminal.shadowRoot.activeElement, initial);
    }
}
"""], cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_command_enter_toggles_terminal_green_button_from_slide(self):
        result = subprocess.run(["node", "-e", r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const elements = new Map();
class HTMLElement {
    attachShadow() {
        const classes = new Set();
        const listeners = {};
        const main = {
            classList: {
                toggle(name) { classes.has(name) ? classes.delete(name) : classes.add(name); },
                contains(name) { return classes.has(name); },
            },
        };
        const green = {
            addEventListener(name, listener) { listeners[name] = listener; },
            click() { listeners.click(); },
        };
        this.shadowRoot = {
            activeElement: null,
            querySelector(selector) { return selector === '#green' ? green : main; },
            contains(node) { return node === main || node === green; },
        };
    }
    getAttribute() { return null; }
}

let terminals = [];
const arrows = { previous: '/1', next: '/3' };
let keydown;
const document = {
    activeElement: null,
    querySelector(selector) { return selector === 'nav-arrows' ? arrows : null; },
    querySelectorAll(selector) { assert.equal(selector, 'web-term'); return terminals; },
    getElementsByTagName() { return []; },
    addEventListener(name, listener, capture) {
        assert.equal(name, 'keydown');
        assert.equal(capture, true);
        keydown = listener;
    },
};
const window = { location: { href: '/2' } };
vm.runInNewContext(fs.readFileSync('.demoit/js/demoit.js', 'utf8'), {
    document,
    window,
    HTMLElement,
    customElements: { define(name, element) { elements.set(name, element); } },
    BroadcastChannel: class { postMessage() {} },
    CurrentStep: 2,
    StepCount: 3,
});

function makeWindow() {
    const terminalWindow = new (elements.get('fake-window'))();
    terminalWindow.connectedCallback();
    terminalWindow.frame = {};
    terminalWindow.contains = node => node === terminalWindow.frame;
    return terminalWindow;
}
function makeTerminal(windows) {
    return {
        shadowRoot: { activeElement: null },
        $$(selector) { assert.equal(selector, 'fake-window'); return windows; },
    };
}
function press(overrides = {}) {
    const event = {
        key: 'Enter', metaKey: true, repeat: false,
        defaultPrevented: false, stopped: false,
        preventDefault() { this.defaultPrevented = true; },
        stopPropagation() { this.stopped = true; },
        ...overrides,
    };
    keydown(event);
    return event;
}
const maximized = terminalWindow => terminalWindow.$('#main').classList.contains('maximized');

// Leave the shortcut alone on slides without terminals.
assert.equal(press().defaultPrevented, false);
const first = makeWindow();
const added = makeWindow();
const second = makeWindow();
const firstTerminal = makeTerminal([first, added]);
const secondTerminal = makeTerminal([second]);
terminals = [firstTerminal, secondTerminal];

assert.equal(press({ metaKey: false }).defaultPrevented, false);
assert.equal(press({ key: 'a' }).defaultPrevented, false);
assert.equal(maximized(first), false);
assert.equal(press().defaultPrevented, true);
assert.equal(maximized(first), true);
assert.equal(press({ repeat: true }).stopped, true);
assert.equal(maximized(first), true);

// The button and shortcut share the same toggle, including restoring size.
first.$('#green').click();
assert.equal(maximized(first), false);
first.$('#green').click();
assert.equal(press().stopped, true);
assert.equal(maximized(first), false);

// Focus inside a shadow-root iframe selects the corresponding terminal.
document.activeElement = secondTerminal;
secondTerminal.shadowRoot.activeElement = second.frame;
press();
assert.equal(maximized(second), true);
assert.equal(maximized(first), false);
assert.equal(document.activeElement, secondTerminal);
assert.equal(secondTerminal.shadowRoot.activeElement, second.frame);
document.activeElement = null;
press();
assert.equal(maximized(second), false);

// A manually maximized window takes priority over focus in an obscured terminal.
document.activeElement = firstTerminal;
firstTerminal.shadowRoot.activeElement = first.frame;
second.$('#green').click();
press();
assert.equal(maximized(second), false);
assert.equal(maximized(first), false);

// Added terminals and their shadow-root window controls are selectable too.
document.activeElement = firstTerminal;
firstTerminal.shadowRoot.activeElement = added.frame;
press();
assert.equal(maximized(added), true);
firstTerminal.shadowRoot.activeElement = added;
added.shadowRoot.activeElement = added.$('#green');
press();
assert.equal(maximized(added), false);

// Existing Command-arrow navigation still works.
assert.equal(press({ key: 'ArrowRight' }).defaultPrevented, true);
assert.equal(window.location.href, '/3');
press({ key: 'ArrowLeft' });
assert.equal(window.location.href, '/1');
"""], cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
