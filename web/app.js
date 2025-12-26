const API_BASE = window.location.hostname.includes('localhost') 
    ? './sample-data.json'
    : 'https://d1dy6umrmzq99l.cloudfront.net';
const flipboardEl = document.getElementById('flipboard');
let flipboardTimer;

const defaultFlips = [
    'FUEL: LOADING MARKETS',
    'FREIGHT: WAITING ON RATES',
    'TRAFFIC: CALIBRATING MAPS',
    'WEATHER: PULLING FORECASTS'
];
const USE_DUMMY_DATA = false;

function randomBetween(min, max) {
    return min + Math.random() * (max - min);
}

function randomInt(min, max) {
    return Math.floor(randomBetween(min, max + 1));
}

function roundTo(value, decimals) {
    const factor = Math.pow(10, decimals);
    return Math.round(value * factor) / factor;
}

function randomChoice(list) {
    return list[randomInt(0, list.length - 1)];
}

function pickSome(list, min, max) {
    const count = randomInt(min, max);
    const pool = list.slice();
    for (let i = pool.length - 1; i > 0; i -= 1) {
        const j = randomInt(0, i);
        [pool[i], pool[j]] = [pool[j], pool[i]];
    }
    return pool.slice(0, count);
}

function calcFuelScore(dieselChange) {
    if (dieselChange > 1.5) {
        return {status: 'RISING', analysis: 'Prices trending up - lock in rates now'};
    }
    if (dieselChange < -1.5) {
        return {status: 'FALLING', analysis: 'Favorable pricing window - good time to fuel'};
    }
    return {status: 'STABLE', analysis: 'Prices holding steady - no immediate action needed'};
}

function calcFreightScore(changes) {
    const avgChange = changes.reduce((sum, value) => sum + value, 0) / changes.length;
    if (avgChange > 3) {
        return {status: 'RATES UP', analysis: 'Strong demand - negotiate higher rates'};
    }
    if (avgChange < -3) {
        return {status: 'RATES DOWN', analysis: 'Soft market - expect rate pressure'};
    }
    return {status: 'STEADY', analysis: 'Balanced market conditions'};
}

function calcTrafficScore(alerts) {
    const count = alerts.length;
    if (count >= 4) {
        return {status: 'CONGESTED', analysis: 'Multiple delays - add buffer time'};
    }
    if (count >= 2) {
        return {status: 'MODERATE', analysis: 'Some delays expected - plan alternate routes'};
    }
    return {status: 'CLEAR', analysis: 'Smooth operations expected'};
}

function calcWeatherScore(forecasts) {
    const highCount = forecasts.filter(item => item.severity === 'high').length;
    if (highCount >= 2) {
        return {status: 'SEVERE', analysis: 'Major disruptions likely - consider delays'};
    }
    if (highCount >= 1) {
        return {status: 'CAUTION', analysis: 'Monitor conditions - prepare for impacts'};
    }
    return {status: 'NORMAL', analysis: 'Conditions favorable for operations'};
}

function buildDisruptionRisk(alerts, forecasts) {
    const highWeather = forecasts.filter(item => item.severity === 'high').length;
    const moderateWeather = forecasts.filter(item => item.severity === 'moderate').length;
    let level = 'LOW';
    let reason = 'Normal operating conditions';
    if (highWeather >= 2 || alerts.length >= 4) {
        level = 'HIGH';
        reason = 'Severe weather or heavy congestion';
    } else if (highWeather >= 1 || moderateWeather >= 1 || alerts.length >= 2) {
        level = 'MODERATE';
        reason = 'Localized delays possible';
    }
    const topConditions = [];
    alerts.slice(0, 2).forEach(alert => topConditions.push(`${alert.reason} (${alert.location})`));
    forecasts.slice(0, 2).forEach(forecast => topConditions.push(`${forecast.condition} (${forecast.corridor})`));
    return {level, reason, top_conditions: topConditions.slice(0, 3)};
}

function generateDummyBriefing() {
    const now = new Date();
    const date = now.toISOString().split('T')[0];
    const nationalAvg = roundTo(randomBetween(3.2, 3.85), 2);
    const diesel = roundTo(nationalAvg + randomBetween(0.4, 0.85), 2);
    const nationalChange = roundTo(randomBetween(-2.4, 2.4), 1);
    const dieselChange = roundTo(randomBetween(-2.4, 2.4), 1);

    const fuelNews = [
        {title: 'Refinery output steady as demand stabilizes', url: '#'},
        {title: 'Crude inventories show modest drawdown', url: '#'},
        {title: 'Gulf Coast pricing tightens ahead of weekend', url: '#'}
    ];

    const fuel = {
        national_avg: nationalAvg,
        national_change: nationalChange,
        diesel,
        diesel_change: dieselChange,
        news: pickSome(fuelNews, 1, 2)
    };

    const dryVan = roundTo(randomBetween(1.9, 2.6), 2);
    const reefer = roundTo(dryVan + randomBetween(0.25, 0.55), 2);
    const flatbed = roundTo(randomBetween(2.45, 3.35), 2);
    const dryVanChange = roundTo(randomBetween(-3.4, 3.4), 1);
    const reeferChange = roundTo(randomBetween(-3.2, 3.2), 1);
    const flatbedChange = roundTo(randomBetween(-3.6, 3.6), 1);

    const freightNews = [
        {title: 'Seasonal freight push keeps contract volumes firm', url: '#'},
        {title: 'Spot market cools as capacity loosens', url: '#'},
        {title: 'Retail restock lifts reefer demand in Midwest', url: '#'}
    ];

    const freight = {
        dry_van: dryVan,
        dry_van_change: dryVanChange,
        reefer,
        reefer_change: reeferChange,
        flatbed,
        flatbed_change: flatbedChange,
        news: pickSome(freightNews, 1, 2)
    };

    const trafficAlertPool = [
        {location: 'I-95 North - VA', reason: 'Construction delays'},
        {location: 'I-10 East - TX', reason: 'Heavy traffic near interchange'},
        {location: 'I-5 South - CA', reason: 'Accident cleanup'},
        {location: 'I-80 West - PA', reason: 'Lane closures'},
        {location: 'I-75 North - GA', reason: 'Event congestion'}
    ];
    const trafficAlerts = pickSome(trafficAlertPool, 0, 3).map(alert => ({
        ...alert,
        severity: randomChoice(['low', 'moderate', 'high'])
    }));
    const trafficNews = [
        {title: 'Metro construction schedules updated for this week', url: '#'},
        {title: 'State DOT reports steady weekday traffic volumes', url: '#'}
    ];
    const traffic = {
        alerts: trafficAlerts,
        news: pickSome(trafficNews, 0, 2)
    };

    const weatherPool = [
        {corridor: 'I-95 Northeast', condition: 'Clear conditions', severity: 'low'},
        {corridor: 'I-80 Midwest', condition: 'Light snow possible', severity: 'moderate'},
        {corridor: 'I-70 Rockies', condition: 'High winds', severity: 'high'},
        {corridor: 'I-40 Southwest', condition: 'Rain showers', severity: 'low'},
        {corridor: 'I-10 Gulf', condition: 'Thunderstorms', severity: 'high'}
    ];
    const forecasts = pickSome(weatherPool, 0, 3);
    const weatherNews = [
        {title: 'Seasonal storm pattern shifts toward Plains', url: '#'},
        {title: 'Visibility improves across major corridors', url: '#'}
    ];
    const weather = {
        forecasts,
        news: pickSome(weatherNews, 0, 2)
    };

    const trafficScore = calcTrafficScore(trafficAlerts);
    const weatherScore = calcWeatherScore(forecasts);

    const aiInsight = `Diesel sits near $${diesel.toFixed(2)}/gal and dry van rates average $${dryVan.toFixed(2)}/mi. ${trafficScore.analysis} ${weatherScore.analysis}`;

    const borderCrossings = [
        {name: 'Ambassador Bridge', base: 25},
        {name: 'Peace Bridge', base: 15},
        {name: 'Laredo World Trade Bridge', base: 45},
        {name: 'Otay Mesa', base: 35},
        {name: 'Pharr International Bridge', base: 30}
    ];
    const border_wait_times = borderCrossings.map(crossing => {
        const wait = Math.max(5, Math.round(crossing.base + randomBetween(-10, 15)));
        let status = 'DELAYED';
        if (wait <= 15) {
            status = 'NORMAL';
        } else if (wait <= 30) {
            status = 'MODERATE';
        }
        return {
            name: crossing.name,
            commercial_wait: wait,
            status
        };
    });

    const economic_data = [
        {
            name: 'Unemployment Rate',
            value: roundTo(randomBetween(3.4, 4.3), 1),
            unit: '%',
            change: roundTo(randomBetween(-0.3, 0.3), 1)
        },
        {
            name: 'Consumer Price Index',
            value: roundTo(randomBetween(303, 312), 1),
            unit: 'Index',
            change: roundTo(randomBetween(-0.4, 0.4), 1)
        },
        {
            name: 'WTI Crude Oil',
            value: roundTo(randomBetween(65, 85), 1),
            unit: '$/barrel',
            change: roundTo(randomBetween(-2.5, 2.5), 1)
        },
        {
            name: 'USD/EUR Exchange',
            value: roundTo(randomBetween(1.02, 1.12), 2),
            unit: 'Rate',
            change: roundTo(randomBetween(-0.03, 0.03), 2)
        },
        {
            name: 'Industrial Production',
            value: roundTo(randomBetween(100, 105), 1),
            unit: 'Index',
            change: roundTo(randomBetween(-0.5, 0.5), 1)
        }
    ];

    const totalFlights = randomInt(3800, 5200);
    const cargoFlights = randomInt(160, 260);
    const hubTemplates = [
        {name: 'Memphis (FDX)'},
        {name: 'Louisville (UPS)'},
        {name: 'Anchorage (ANC)'},
        {name: 'Miami (MIA)'}
    ];
    const major_hubs = hubTemplates.map(hub => {
        const flights = randomInt(18, 50);
        let status = 'QUIET';
        if (flights >= 40) {
            status = 'BUSY';
        } else if (flights >= 25) {
            status = 'NORMAL';
        }
        return {...hub, flights, status};
    });

    const air_traffic = {
        total_flights_in_bbox: totalFlights,
        cargo_flights: cargoFlights,
        major_hubs
    };

    const aisPortTemplates = [
        {name: 'Los Angeles', base: 85},
        {name: 'Long Beach', base: 72},
        {name: 'New York/New Jersey', base: 68},
        {name: 'Savannah', base: 45},
        {name: 'Seattle', base: 38},
        {name: 'Houston', base: 52}
    ];
    const baseDateTime = now.toISOString();
    const ais_data = aisPortTemplates.map(port => {
        const vessels = Math.max(20, Math.round(port.base + randomBetween(-12, 12)));
        let congestion = 'LOW';
        if (vessels > 70) {
            congestion = 'HIGH';
        } else if (vessels > 45) {
            congestion = 'MODERATE';
        }
        return {
            port_name: port.name,
            vessels_in_area: vessels,
            congestion_level: congestion,
            BaseDateTime: baseDateTime
        };
    });

    const eventTemplates = [
        {title: 'Port congestion eases at major West Coast terminals', source: 'logistics-news.com'},
        {title: 'Rail service disruption reported near Chicago hub', source: 'freightwire.net'},
        {title: 'Fuel supply tightens in Gulf region', source: 'energy-watch.com'},
        {title: 'Border staffing delays commercial traffic', source: 'trade-weekly.com'},
        {title: 'Severe weather impacts Gulf shipping lanes', source: 'maritime-today.com'}
    ];
    const global_events = pickSome(eventTemplates, 2, 4).map(event => ({
        ...event,
        impact_level: randomChoice(['LOW', 'MEDIUM', 'HIGH'])
    }));

    return {
        date,
        ai_insight: aiInsight,
        fuel,
        fuel_score: calcFuelScore(dieselChange),
        freight,
        freight_score: calcFreightScore([dryVanChange, reeferChange, flatbedChange]),
        traffic,
        traffic_score: trafficScore,
        weather,
        weather_score: weatherScore,
        disruption_risk: buildDisruptionRisk(trafficAlerts, forecasts),
        border_wait_times,
        economic_data,
        air_traffic,
        ais_data,
        global_events
    };
}

function updateTimezones() {
    const now = new Date();
    const est = now.toLocaleTimeString('en-US', {timeZone: 'America/New_York', hour: '2-digit', minute: '2-digit'});
    const cst = now.toLocaleTimeString('en-US', {timeZone: 'America/Chicago', hour: '2-digit', minute: '2-digit'});
    const pst = now.toLocaleTimeString('en-US', {timeZone: 'America/Los_Angeles', hour: '2-digit', minute: '2-digit'});
    document.getElementById('timezones').textContent = `EST ${est} | CST ${cst} | PST ${pst}`;
}

async function loadBriefing() {
    if (USE_DUMMY_DATA) {
        renderBriefing(generateDummyBriefing());
        return;
    }
    try {
        const now = new Date();
        const today = new Intl.DateTimeFormat('en-CA', {
            timeZone: 'America/New_York'
        }).format(now);
        const url = window.location.hostname.includes('localhost') 
            ? API_BASE 
            : `https://d1dy6umrmzq99l.cloudfront.net/${today}.json`;
        const response = await fetch(url);
        
        if (!response.ok) throw new Error('No briefing available');
        
        const data = await response.json();
        renderBriefing(data);
    } catch (error) {
        console.error('Failed to load briefing:', error);
        renderBriefing(generateDummyBriefing());
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
    renderEconomicData(data.economic_data);
    renderBorderWaitTimes(data.border_wait_times);
    renderAirTraffic(data.air_traffic);
    renderAISData(data.ais_data);
    renderGlobalEvents(data.global_events);
    renderBorderWaitTimes(data.border_wait_times);
    renderEconomicData(data.economic_data);
    renderAirTraffic(data.air_traffic);
    renderAisData(data.ais_data);
    renderGlobalEvents(data.global_events);

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

function renderBorderWaitTimes(data) {
    const el = document.getElementById('border-wait-times-data');
    if (!data || data.length === 0) {
        el.innerHTML = '<p class="loading">NO DATA</p>';
        return;
    }
    let html = data.map(port => `
        <div class="metric">
            <span class="metric-label">${port.port_name}</span>
            <span class="metric-value">${port.standard_lanes_wait_minutes} MIN</span>
        </div>
    `).join('');
    el.innerHTML = html;
}

function renderEconomicData(data) {
    const el = document.getElementById('economic-data-data');
    if (!data || data.length === 0) {
        el.innerHTML = '<p class="loading">NO DATA</p>';
        return;
    }
    let html = data.map(series => {
        const value = series.series_id.includes('GAS') || series.series_id.includes('OIL') 
            ? `$${parseFloat(series.value).toFixed(2)}` 
            : parseFloat(series.value).toFixed(2);
        return `
            <div class="metric">
                <span class="metric-label">${series.series_name}</span>
                <span class="metric-value">${value}</span>
            </div>
        `;
    }).join('');
    el.innerHTML = html;
}

function renderAirTraffic(data) {
    const el = document.getElementById('air-traffic-data');
    const totalFlights = data?.total_flights_in_bbox || 0;
    if (!totalFlights) {
        el.innerHTML = '<p class="loading">NO FLIGHTS</p>';
        return;
    }
    el.innerHTML = `
        <div class="metric">
            <span class="metric-label">FLIGHTS IN U.S. AIRSPACE</span>
            <span class="metric-value">${totalFlights.toLocaleString()}</span>
        </div>
        <p style="font-size:0.7rem;color:#666;text-align:center;padding:0.5rem 1rem;">
            Displaying a summary of total flights. Detailed view coming soon.
        </p>
    `;
}

function renderAisData(data) {
    const el = document.getElementById('ais-data-data');
    const sampleSize = data?.length || 0;
    if (sampleSize === 0) {
        el.innerHTML = '<p class="loading">NO DATA</p>';
        return;
    }
    el.innerHTML = `
        <div class="metric">
            <span class="metric-label">VESSELS SAMPLED (U.S.)</span>
            <span class="metric-value">${sampleSize}</span>
        </div>
        <p style="font-size:0.7rem;color:#666;text-align:center;padding:0.5rem 1rem;">
            Displaying a sample of vessels from ${data[0]?.BaseDateTime?.split('T')[0] || 'yesterday'}.
        </p>
    `;
}

function renderGlobalEvents(data) {
    const el = document.getElementById('global-events-data');
    if (!data || data.length === 0) {
        el.innerHTML = '<p class="loading">NO MAJOR EVENTS</p>';
        return;
    }
    let html = data.map(event => `
        <div class="alert">
            <div class="alert-location" style="color:#ffaa00;">${event.Location}, ${event.Country}</div>
            <div class="alert-reason" style="font-size:0.7rem">
                Goldstein Scale: ${event.GoldsteinScale.toFixed(2)}
                <a href="${event.SourceURL}" target="_blank" style="color:#999;text-decoration:none;margin-left:0.5rem;">&#128279;</a>
            </div>
        </div>
    `).join('');
    el.innerHTML = html;
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
    document.getElementById('border-wait-times-data').innerHTML = '<p class="loading">DATA UNAVAILABLE</p>';
    document.getElementById('economic-data-data').innerHTML = '<p class="loading">DATA UNAVAILABLE</p>';
    document.getElementById('air-traffic-data').innerHTML = '<p class="loading">DATA UNAVAILABLE</p>';
    document.getElementById('ais-data-data').innerHTML = '<p class="loading">DATA UNAVAILABLE</p>';
    document.getElementById('global-events-data').innerHTML = '<p class="loading">DATA UNAVAILABLE</p>';
    startFlipboard(defaultFlips);
}

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
if (!hasSeenIntro && introModal) {
    setTimeout(() => {
        introModal.classList.add('hidden');
        localStorage.setItem('logistix-intro-seen', 'true');
    }, 6000);
}

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

function renderEconomicData(data) {
    const container = document.getElementById('economic-data-data');
    if (!data || !Array.isArray(data) || data.length === 0) {
        container.innerHTML = '<p class="loading">NO DATA AVAILABLE</p>';
        return;
    }
    
    let html = '';
    data.forEach(indicator => {
        const changeColor = indicator.change > 0 ? '#ff0000' : indicator.change < 0 ? '#00ff00' : '#ffaa00';
        const changeSign = indicator.change > 0 ? '+' : '';
        html += `
            <div class="metric">
                <span class="metric-label">${indicator.name}</span>
                <span class="metric-value">${indicator.value} ${indicator.unit} <span style="color:${changeColor};">${changeSign}${indicator.change}</span></span>
            </div>
        `;
    });
    container.innerHTML = html;
}

function renderBorderWaitTimes(data) {
    const container = document.getElementById('border-wait-times-data');
    if (!data || !Array.isArray(data) || data.length === 0) {
        container.innerHTML = '<p class="loading">NO DATA AVAILABLE</p>';
        return;
    }
    
    let html = '';
    data.forEach(crossing => {
        const statusColor = crossing.status === 'NORMAL' ? '#00ff00' : crossing.status === 'MODERATE' ? '#ffaa00' : '#ff0000';
        html += `
            <div class="metric">
                <span class="metric-label">${crossing.name}</span>
                <span class="metric-value">${crossing.commercial_wait}min <span style="color:${statusColor};">${crossing.status}</span></span>
            </div>
        `;
    });
    container.innerHTML = html;
}

function renderAirTraffic(data) {
    const container = document.getElementById('air-traffic-data');
    if (!data || typeof data !== 'object') {
        container.innerHTML = '<p class="loading">NO DATA AVAILABLE</p>';
        return;
    }
    
    let html = `
        <div class="metric">
            <span class="metric-label">TOTAL FLIGHTS</span>
            <span class="metric-value">${data.total_flights_in_bbox || 0}</span>
        </div>
        <div class="metric">
            <span class="metric-label">CARGO FLIGHTS</span>
            <span class="metric-value">${data.cargo_flights || 0}</span>
        </div>
    `;
    
    if (data.major_hubs && Array.isArray(data.major_hubs)) {
        html += '<div style="margin-top:1rem;padding-top:1rem;border-top:1px solid #333;"><div style="color:#999;font-size:0.7rem;margin-bottom:0.5rem;">MAJOR HUBS</div>';
        data.major_hubs.forEach(hub => {
            const statusColor = hub.status === 'BUSY' ? '#ff0000' : hub.status === 'NORMAL' ? '#00ff00' : '#ffaa00';
            html += `<div style="margin-bottom:0.5rem;font-size:0.75rem;"><span style="color:#aaa;">${hub.name}:</span> <span style="color:${statusColor};">${hub.flights} flights (${hub.status})</span></div>`;
        });
        html += '</div>';
    }
    
    container.innerHTML = html;
}

function renderAISData(data) {
    const container = document.getElementById('ais-data-data');
    if (!data || !Array.isArray(data) || data.length === 0) {
        container.innerHTML = '<p class="loading">NO DATA AVAILABLE</p>';
        return;
    }
    
    let html = '';
    data.slice(0, 4).forEach(port => {
        const congestionColor = port.congestion_level === 'HIGH' ? '#ff0000' : port.congestion_level === 'MODERATE' ? '#ffaa00' : '#00ff00';
        html += `
            <div class="metric">
                <span class="metric-label">${port.port_name}</span>
                <span class="metric-value">${port.vessels_in_area} vessels <span style="color:${congestionColor};">${port.congestion_level}</span></span>
            </div>
        `;
    });
    container.innerHTML = html;
}

function renderGlobalEvents(data) {
    const container = document.getElementById('global-events-data');
    if (!data || !Array.isArray(data) || data.length === 0) {
        container.innerHTML = '<p class="loading">NO EVENTS DETECTED</p>';
        return;
    }
    
    let html = '';
    data.forEach(event => {
        const impactColor = event.impact_level === 'HIGH' ? '#ff0000' : event.impact_level === 'MEDIUM' ? '#ffaa00' : '#00ff00';
        html += `
            <div style="margin-bottom:1rem;padding:8px;border-left:3px solid ${impactColor};background:#1a1a1a;">
                <div style="font-size:0.75rem;font-weight:700;margin-bottom:0.25rem;">${event.title}</div>
                <div style="font-size:0.65rem;color:#999;">${event.source} • <span style="color:${impactColor};">${event.impact_level} IMPACT</span></div>
            </div>
        `;
    });
    container.innerHTML = html;
}
