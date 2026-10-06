const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

test('briefing renders each new data panel once and preserves maritime details', () => {
    const elements = new Map();
    const writes = new Map();
    const document = {
        getElementById(id) {
            if (!elements.has(id)) {
                const element = {
                    textContent: '', style: {},
                    classList: { add() {}, remove() {} },
                    addEventListener() {}, appendChild() {},
                };
                let html = '';
                Object.defineProperty(element, 'innerHTML', {
                    get: () => html,
                    set(value) { html = value; writes.set(id, (writes.get(id) || 0) + 1); },
                });
                elements.set(id, element);
            }
            return elements.get(id);
        },
        createElement: () => ({ style: {} }),
    };
    const context = vm.createContext({
        document, console,
        window: { location: { hostname: 'localhost' } },
        localStorage: { getItem: () => 'true', setItem() {} },
        setInterval() {}, clearInterval() {}, setTimeout() {},
        fetch: () => new Promise(() => {}), // Prevent live data requests.
    });
    const script = fs.readFileSync(path.join(__dirname, '..', 'web', 'app.js'), 'utf8');
    vm.runInContext(script, context);
    vm.runInContext('renderBriefing(generateDummyBriefing())', context);
    for (const id of ['economic-data-data', 'border-wait-times-data', 'air-traffic-data',
                      'ais-data-data', 'global-events-data']) {
        assert.equal(writes.get(id), 1, `${id} should render once`);
        assert.ok(elements.get(id).innerHTML.length > 0);
    }
    assert.match(elements.get('ais-data-data').innerHTML, /vessels/);
    assert.doesNotMatch(elements.get('ais-data-data').innerHTML, /VESSELS SAMPLED/);
});
