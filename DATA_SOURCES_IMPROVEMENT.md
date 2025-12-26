# Data Sources Improvement Plan

## Priority 1: Freight Data (Critical)

### Current Issue
- Hardcoded static rates from December 2025
- No real market data integration

### Recommended Solutions

**Option A: DAT API (Premium)**
- Source: DAT Trendlines API
- Cost: ~$500-1000/month
- Data: Real-time spot rates, contract rates, load-to-truck ratios
- Coverage: National, equipment-specific

**Option B: FreightWaves SONAR (Premium)**
- Source: FreightWaves SONAR API
- Cost: ~$300-800/month
- Data: Market rates, capacity data, tender volumes

**Option C: Truckstop.com API (Mid-tier)**
- Source: Truckstop.com Load Board API
- Cost: ~$200-400/month
- Data: Posted rates, load availability

**Option D: Web Scraping (Budget)**
- Sources: Public freight reports, industry publications
- Cost: Development time only
- Reliability: Lower, requires maintenance

## Priority 2: Traffic Data (High)

### Current Issue
- Limited to California (511 SF Bay API)
- No national traffic coverage

### Recommended Solutions

**Option A: HERE Traffic API (Premium)**
- Coverage: Global, real-time traffic
- Cost: ~$0.50-2.00 per 1000 requests
- Features: Incidents, flow data, ETA calculations

**Option B: Google Maps Traffic API (Premium)**
- Coverage: Global, excellent accuracy
- Cost: ~$5-17 per 1000 requests
- Features: Real-time conditions, incidents

**Option C: Multiple 511 APIs (Budget)**
- Sources: State DOT 511 systems
- Cost: Free (most states)
- Coverage: State-by-state implementation needed
- States with APIs: CA, NY, FL, TX, WA, OR, NV, CO

**Option D: INRIX API (Premium)**
- Coverage: North America, Europe
- Cost: Enterprise pricing
- Features: Predictive traffic, truck-specific routing

## Priority 3: Enhanced Fuel Data (Medium)

### Current Strengths
- EIA API provides accurate national data
- Government source, reliable

### Improvements Needed

**Regional Breakdown Enhancement**
```python
# Add EIA regional series IDs
REGIONAL_SERIES = {
    'PADD1': 'EMD_EPD2D_PTE_R10_DPG',  # East Coast
    'PADD2': 'EMD_EPD2D_PTE_R20_DPG',  # Midwest  
    'PADD3': 'EMD_EPD2D_PTE_R30_DPG',  # Gulf Coast
    'PADD4': 'EMD_EPD2D_PTE_R40_DPG',  # Rocky Mountain
    'PADD5': 'EMD_EPD2D_PTE_R50_DPG'   # West Coast
}
```

**Additional Fuel Metrics**
- Crude oil prices (WTI, Brent)
- Fuel futures contracts
- Regional price differentials
- Seasonal trends

## Priority 4: Weather Enhancements (Low)

### Current Strengths
- Good coverage with Open-Meteo + NWS
- Real-time alerts integration

### Minor Improvements
- Add more corridor points
- Include wind speed for high-profile vehicles
- Road surface temperature for ice conditions

## Implementation Strategy

### Phase 1: Freight Data (Month 1)
1. Evaluate API options with trial accounts
2. Implement DAT or FreightWaves integration
3. Add rate validation and anomaly detection
4. Create fallback to manual updates

### Phase 2: Traffic Expansion (Month 2)
1. Implement HERE or Google Maps API
2. Add major interstate corridors
3. Create incident severity scoring
4. Add predictive delay calculations

### Phase 3: Data Quality (Month 3)
1. Add data freshness monitoring
2. Implement source reliability scoring
3. Create data validation pipelines
4. Add historical trend analysis

## Cost Analysis

### Budget Option (~$50/month)
- Multiple 511 APIs for traffic
- Web scraping for freight rates
- Current EIA + weather sources

### Standard Option (~$500/month)
- Truckstop.com API for freight
- HERE Traffic API (limited usage)
- Enhanced EIA regional data

### Premium Option (~$1500/month)
- DAT or FreightWaves for freight
- Google Maps Traffic API
- Full regional fuel breakdowns
- Advanced analytics and predictions

## Data Quality Metrics

### Reliability Scoring
```python
def calculate_source_reliability(source_name: str, last_update: datetime) -> float:
    age_hours = (datetime.utcnow() - last_update).total_seconds() / 3600
    
    thresholds = {
        'fuel': 24,      # Daily updates acceptable
        'freight': 4,    # 4-hour max for market rates
        'traffic': 0.25, # 15-minute max for incidents
        'weather': 1     # Hourly updates acceptable
    }
    
    max_age = thresholds.get(source_name, 24)
    return max(0, 1 - (age_hours / max_age))
```

### Data Validation
- Cross-reference multiple sources
- Detect anomalous values (>20% change)
- Validate geographic consistency
- Check temporal patterns

## Alternative Data Sources

### Freight Market Intelligence
- OOIDA (Owner-Operator Independent Drivers Association)
- ATA (American Trucking Associations) reports
- FMCSA data on carrier operations
- Port authority cargo volumes

### Traffic & Infrastructure
- State DOT construction schedules
- Bridge height/weight restrictions
- Weigh station locations and hours
- Truck parking availability

### Economic Indicators
- Diesel fuel tax rates by state
- Seasonal demand patterns
- Industrial production indices
- Consumer spending trends