const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

function dashboard(fetch = () => new Promise(() => {})) {
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
        document, console: { error() {} },
        window: { location: { hostname: 'localhost' } },
        localStorage: { getItem: () => 'true', setItem() {} },
        setInterval() {}, clearInterval() {}, setTimeout() {},
        fetch, // Stubbed requests only; tests never fetch live data.
    });
    const script = fs.readFileSync(path.join(__dirname, '..', 'web', 'app.js'), 'utf8');
    vm.runInContext(script, context);
    return { context, elements, writes };
}

test('briefing renders each new data panel once and preserves maritime details', () => {
    const { context, elements, writes } = dashboard();
    vm.runInContext('renderBriefing(generateDummyBriefing())', context);
    for (const id of ['economic-data-data', 'border-wait-times-data', 'air-traffic-data',
                      'ais-data-data', 'global-events-data']) {
        assert.equal(writes.get(id), 1, `${id} should render once`);
        assert.ok(elements.get(id).innerHTML.length > 0);
    }
    assert.match(elements.get('ais-data-data').innerHTML, /vessels/);
    assert.doesNotMatch(elements.get('ais-data-data').innerHTML, /VESSELS SAMPLED/);
});


for (const [scenario, request] of [
    ['HTTP 404', async () => ({ ok: false })],
    ['network failure', async () => { throw new Error('offline'); }],
    ['invalid JSON', async () => ({ ok: true, json: async () => { throw new SyntaxError('invalid JSON'); } })],
]) {
    test(`load failure (${scenario}) clears old metrics without manufacturing data`, async () => {
        const { context, elements } = dashboard();
        vm.runInContext('renderBriefing(generateDummyBriefing())', context);
        assert.match(elements.get('fuel-data').innerHTML, /DIESEL/);
        context.fetch = request;
        await vm.runInContext('loadBriefing()', context);
        assert.match(elements.get('ai-insight').textContent, /UNABLE TO LOAD/);
        assert.equal(elements.get('risk').textContent, 'DISRUPTION RISK: UNKNOWN');
        assert.equal(elements.get('insight-timestamp').textContent, '');
        for (const id of ['fuel-data', 'freight-data', 'traffic-data', 'weather-data',
                          'economic-data-data', 'border-wait-times-data', 'air-traffic-data',
                          'ais-data-data', 'global-events-data']) {
            assert.match(elements.get(id).innerHTML, /DATA UNAVAILABLE/);
            assert.doesNotMatch(elements.get(id).innerHTML, /metric-value/);
        }
    });
}
