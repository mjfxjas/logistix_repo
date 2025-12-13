const API_BASE = 'https://logistix-data-dev.s3.us-east-1.amazonaws.com';
const flipboardEl = document.getElementById('flipboard');
let flipboardTimer;

const defaultFlips = [
    'FUEL: LOADING MARKETS',
    'FREIGHT: WAITING ON RATES',
    'TRAFFIC: CALIBRATING MAPS',
    'WEATHER: PULLING FORECASTS'
];

function updateTimezones() {
    const now = new Date();
    const est = now.toLocaleTimeString('en-US', {timeZone: 'America/New_York', hour: '2-digit', minute: '2-digit'});
    const cst = now.toLocaleTimeString('en-US', {timeZone: 'America/Chicago', hour: '2-digit', minute: '2-digit'});
    const pst = now.toLocaleTimeString('en-US', {timeZone: 'America/Los_Angeles', hour: '2-digit', minute: '2-digit'});
    document.getElementById('timezones').textContent = `EST ${est} | CST ${cst} | PST ${pst}`;
}

async function loadBriefing() {
    try {
        const now = new Date();
        const estDate = now.toLocaleDateString('en-US', {timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit'});
        const [month, day, year] = estDate.split('/');
        const today = `${year}-${month}-${day}`;
        const response = await fetch(`${API_BASE}/${today}.json`);
        
        if (!response.ok) throw new Error('No briefing available');
        
        const data = await response.json();
        renderBriefing(data);
    } catch (error) {
        renderError();
    }
}

function renderBriefing(data) {
    const now = new Date();
    const estDateStr = now.toLocaleDateString('en-US', {timeZone: 'America/New_York', year: 'numeric', month: 'long', day: 'numeric', weekday: 'long'});
    document.getElementById('date').textContent = estDateStr.toUpperCase();
    document.getElementById('ai-insight').textContent = data.ai_insight || 'NO INSIGHT AVAILABLE';
    
    const insightDate = new Date().toLocaleDateString('en-US', { 
        timeZone: 'America/New_York',
        month: 'short', 
        day: 'numeric', 
        year: 'numeric' 
    });
    document.getElementById('insight-timestamp').textContent = `${insightDate} 5:59 AM ET`;
    
    const risk = data.disruption_risk || {level: 'LOW', reason: 'No data', top_conditions: []};
    const level = risk.level || risk;
    const reason = risk.reason || '';
    const topConditions = risk.top_conditions || [];
    const riskColor = level === 'HIGH' ? '#ff0000' : level === 'MODERATE' ? '#ffaa00' : '#00ff00';
    
    let riskText = `DISRUPTION RISK: <span style="color:${riskColor};font-weight:700;">${level}</span>${reason ? ` - ${reason}` : ''}`;
    if (topConditions.length > 0) {
        riskText += `<br><span style="font-size:0.75rem;color:#999;">${topConditions.join(' | ')}</span>`;
    }
    document.getElementById('risk').innerHTML = riskText;
    
    renderFuel(data.fuel, data.fuel_score);
    renderFreight(data.freight, data.freight_score);
    renderTraffic(data.traffic, data.traffic_score);
    renderWeather(data.weather, data.weather_score);

    startFlipboard(buildFlipMessages(data));
}

function renderFuel(fuel, score) {
    const status = score?.status || score || 'STABLE';
    const analysis = score?.analysis || '';
    const options = ['FALLING', 'STABLE', 'RISING'];
    const colors = ['#00ff00', '#ffaa00', '#ff0000'];
    const scoreHtml = score ? `<div style="padding:0.5rem 1rem;background:#1a1a1a;border-bottom:1px solid #333;font-size:0.75rem;">
        <div style="color:#999;margin-bottom:0.25rem;">${options.map((o, i) => o === status ? `<span style="color:${colors[i]};font-weight:700;">${o}</span>` : `<span style="color:#666;">${o}</span>`).join(' | ')}</div>
        ${analysis ? `<div style="color:#aaa;font-size:0.7rem;font-style:italic;">${analysis}</div>` : ''}
    </div>` : '';
    let html = scoreHtml + `
        <div class="metric">
            <span class="metric-label">NATIONAL AVG</span>
            <span class="metric-value">$${fuel.national_avg.toFixed(2)}/GAL ${renderChange(fuel.national_change)}</span>
        </div>
        <div class="metric">
            <span class="metric-label">DIESEL</span>
            <span class="metric-value">$${fuel.diesel.toFixed(2)}/GAL ${renderChange(fuel.diesel_change)}</span>
        </div>
    `;
    if (fuel.news && fuel.news.length > 0) {
        html += '<div style="margin-top:1rem;padding-top:1rem;border-top:1px solid #333;"><div style="color:#999;font-size:0.7rem;margin-bottom:0.5rem;">NEWS</div>';
        fuel.news.forEach(item => {
            html += `<div style="margin-bottom:0.5rem;"><a href="${item.url}" target="_blank" class="news-link" style="color:#aaa;font-size:0.75rem;text-decoration:none;">${item.title}</a></div>`;
        });
        html += '</div>';
    }
    document.getElementById('fuel-data').innerHTML = html;
}

function renderFreight(freight, score) {
    const status = score?.status || score || 'STEADY';
    const analysis = score?.analysis || '';
    const options = ['RATES DOWN', 'STEADY', 'RATES UP'];
    const colors = ['#00ff00', '#ffaa00', '#ff0000'];
    const scoreHtml = score ? `<div style="padding:0.5rem 1rem;background:#1a1a1a;border-bottom:1px solid #333;font-size:0.75rem;">
        <div style="color:#999;margin-bottom:0.25rem;">${options.map((o, i) => o === status ? `<span style="color:${colors[i]};font-weight:700;">${o}</span>` : `<span style="color:#666;">${o}</span>`).join(' | ')}</div>
        ${analysis ? `<div style="color:#aaa;font-size:0.7rem;font-style:italic;">${analysis}</div>` : ''}
    </div>` : '';
    let html = scoreHtml + `
        <div class="metric">
            <span class="metric-label">DRY VAN</span>
            <span class="metric-value">$${freight.dry_van.toFixed(2)}/MI ${renderChange(freight.dry_van_change)}</span>
        </div>
        <div class="metric">
            <span class="metric-label">REEFER</span>
            <span class="metric-value">$${freight.reefer.toFixed(2)}/MI ${renderChange(freight.reefer_change)}</span>
        </div>
        <div class="metric">
            <span class="metric-label">FLATBED</span>
            <span class="metric-value">$${freight.flatbed.toFixed(2)}/MI ${renderChange(freight.flatbed_change)}</span>
        </div>
    `;
    if (freight.news && freight.news.length > 0) {
        html += '<div style="margin-top:1rem;padding-top:1rem;border-top:1px solid #333;"><div style="color:#999;font-size:0.7rem;margin-bottom:0.5rem;">NEWS</div>';
        freight.news.forEach(item => {
            html += `<div style="margin-bottom:0.5rem;"><a href="${item.url}" target="_blank" class="news-link" style="color:#aaa;font-size:0.75rem;text-decoration:none;">${item.title}</a></div>`;
        });
        html += '</div>';
    }
    document.getElementById('freight-data').innerHTML = html;
}

function renderTraffic(trafficData, score) {
    const status = score?.status || score || 'CLEAR';
    const analysis = score?.analysis || '';
    const options = ['CLEAR', 'MODERATE', 'CONGESTED'];
    const colors = ['#00ff00', '#ffaa00', '#ff0000'];
    const scoreHtml = score ? `<div style="padding:0.5rem 1rem;background:#1a1a1a;border-bottom:1px solid #333;font-size:0.75rem;">
        <div style="color:#999;margin-bottom:0.25rem;">${options.map((o, i) => o === status ? `<span style="color:${colors[i]};font-weight:700;">${o}</span>` : `<span style="color:#666;">${o}</span>`).join(' | ')}</div>
        ${analysis ? `<div style="color:#aaa;font-size:0.7rem;font-style:italic;">${analysis}</div>` : ''}
    </div>` : '';
    
    let html = scoreHtml;
    const traffic = trafficData?.alerts || trafficData || [];
    
    if (!traffic || traffic.length === 0) {
        html += '<p class="loading">NO MAJOR ALERTS</p>';
    } else {
        html += traffic.map(alert => `
            <div class="alert">
                <div class="alert-location">${alert.location}</div>
                <div class="alert-reason">${alert.reason}</div>
            </div>
        `).join('');
    }
    
    if (trafficData?.news && trafficData.news.length > 0) {
        html += '<div style="margin-top:1rem;padding-top:1rem;border-top:1px solid #333;"><div style="color:#999;font-size:0.7rem;margin-bottom:0.5rem;">NEWS</div>';
        trafficData.news.forEach(item => {
            html += `<div style="margin-bottom:0.5rem;"><a href="${item.url}" target="_blank" class="news-link" style="color:#aaa;font-size:0.75rem;text-decoration:none;">${item.title}</a></div>`;
        });
        html += '</div>';
    }
    
    document.getElementById('traffic-data').innerHTML = html;
}

function renderWeather(weatherData, score) {
    const status = score?.status || score || 'NORMAL';
    const analysis = score?.analysis || '';
    const options = ['NORMAL', 'CAUTION', 'SEVERE'];
    const colors = ['#00ff00', '#ffaa00', '#ff0000'];
    const scoreHtml = score ? `<div style="padding:0.5rem 1rem;background:#1a1a1a;border-bottom:1px solid #333;font-size:0.75rem;">
        <div style="color:#999;margin-bottom:0.25rem;">${options.map((o, i) => o === status ? `<span style="color:${colors[i]};font-weight:700;">${o}</span>` : `<span style="color:#666;">${o}</span>`).join(' | ')}</div>
        ${analysis ? `<div style="color:#aaa;font-size:0.7rem;font-style:italic;">${analysis}</div>` : ''}
    </div>` : '';
    
    let html = scoreHtml;
    const weather = weatherData?.forecasts || weatherData || [];
    
    if (!weather || weather.length === 0) {
        html += '<p class="loading">NO MAJOR DISRUPTIONS</p>';
    } else {
        html += weather.map(w => `
            <div class="metric">
                <span class="metric-label">${w.corridor}</span>
                <span class="metric-value">${w.condition.toUpperCase()}</span>
            </div>
        `).join('');
    }
    
    if (weatherData?.news && weatherData.news.length > 0) {
        html += '<div style="margin-top:1rem;padding-top:1rem;border-top:1px solid #333;"><div style="color:#999;font-size:0.7rem;margin-bottom:0.5rem;">NEWS</div>';
        weatherData.news.forEach(item => {
            html += `<div style="margin-bottom:0.5rem;"><a href="${item.url}" target="_blank" class="news-link" style="color:#aaa;font-size:0.75rem;text-decoration:none;">${item.title}</a></div>`;
        });
        html += '</div>';
    }
    
    document.getElementById('weather-data').innerHTML = html;
}

function renderChange(change) {
    if (!change) return '';
    const sign = change > 0 ? '+' : '';
    const className = change > 0 ? 'change-up' : 'change-down';
    return `<span class="${className}">${sign}${change.toFixed(1)}%</span>`;
}

function formatDate(dateStr) {
    const date = new Date();
    return date.toLocaleDateString('en-US', { 
        timeZone: 'America/New_York',
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    }).toUpperCase();
}

function renderError() {
    document.getElementById('ai-insight').textContent = 'UNABLE TO LOAD BRIEFING. CHECK BACK LATER.';
    document.getElementById('fuel-data').innerHTML = '<p class="loading">DATA UNAVAILABLE</p>';
    document.getElementById('freight-data').innerHTML = '<p class="loading">DATA UNAVAILABLE</p>';
    document.getElementById('traffic-data').innerHTML = '<p class="loading">DATA UNAVAILABLE</p>';
    document.getElementById('weather-data').innerHTML = '<p class="loading">DATA UNAVAILABLE</p>';
    startFlipboard(defaultFlips);
}

document.getElementById('subscribe-btn').addEventListener('click', () => {
    alert('SUBSCRIPTION FEATURE COMING SOON');
});

// Intro modal logic
const introModal = document.getElementById('intro-modal');
const introClose = document.getElementById('intro-close');
const hasSeenIntro = localStorage.getItem('logistix-intro-seen');

if (hasSeenIntro) {
    introModal.classList.add('hidden');
}

introClose.addEventListener('click', () => {
    introModal.classList.add('hidden');
    localStorage.setItem('logistix-intro-seen', 'true');
});

updateTimezones();
setInterval(updateTimezones, 1000);
loadBriefing();
setInterval(loadBriefing, 300000); // Refresh data every 5 minutes

function buildFlipMessages(data) {
    if (!data) return defaultFlips;
    const msgs = [];
    if (data.fuel) {
        msgs.push(`FUEL AVG $${data.fuel.national_avg.toFixed(2)}/GAL`);
        msgs.push(`DIESEL $${data.fuel.diesel.toFixed(2)}/GAL`);
    }
    if (data.freight) {
        msgs.push(`DRY VAN $${data.freight.dry_van.toFixed(2)}/MI`);
        msgs.push(`REEFER $${data.freight.reefer.toFixed(2)}/MI`);
        msgs.push(`FLATBED $${data.freight.flatbed.toFixed(2)}/MI`);
    }
    if (data.traffic?.alerts?.length) {
        const t = data.traffic.alerts[0];
        msgs.push(`TRAFFIC ${t.location.toUpperCase()}`);
    }
    if (data.weather?.forecasts?.length) {
        const w = data.weather.forecasts[0];
        msgs.push(`WX ${w.corridor.toUpperCase()}: ${w.condition.toUpperCase()}`);
    }
    const risk = data.disruption_risk;
    if (risk?.level) {
        msgs.push(`RISK ${risk.level.toUpperCase()}`);
    }
    return msgs.length ? msgs : defaultFlips;
}

function startFlipboard(messages) {
    if (!flipboardEl) return;
    const list = messages && messages.length ? messages : defaultFlips;
    if (flipboardTimer) clearInterval(flipboardTimer);

    const renderMessage = (msg) => {
        flipboardEl.innerHTML = '';
        const padded = msg.padEnd(28, ' ');
        padded.split('').forEach((char, idx) => {
            const span = document.createElement('span');
            span.className = 'flap';
            span.textContent = char;
            span.style.animationDelay = `${idx * 0.02}s`;
            flipboardEl.appendChild(span);
        });
        flipboardEl.classList.add('is-flipping');
        setTimeout(() => flipboardEl.classList.remove('is-flipping'), 280);
    };

    let current = 0;
    renderMessage(list[current]);
    flipboardTimer = setInterval(() => {
        current = (current + 1) % list.length;
        const msg = list[current];
        renderMessage(msg);
    }, 4200);
}
