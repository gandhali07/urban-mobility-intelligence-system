# Urban Mobility Business Insights

These insights are written for presentation slides. Each item is a business question, one key metric, and one takeaway.

## 1. Event Impact

**Question:** Do citywide events make taxi trips slower?

**Key metric:** High-event days average 16.2 min vs no-event days 16.4 min.

**Insight:** Citywide event volume alone does not show a meaningful difference in trip delay in this sample.

**Why it matters:** For better planning, future work should measure events near pickup/dropoff zones instead of only counting all NYC events.

**Suggested chart:** `event_impact_duration.png`

## 2. Weather Impact

**Question:** Does weather change taxi travel time?

**Key metric:** Slowest temperature band: mild at 17.6 min.

**Insight:** Weather changes trip duration, but the gap between mild and freezing is smaller than distance and location effects.

**Why it matters:** Weather is useful context, but business decisions should prioritize distance, zones, and time of day first.

**Suggested chart:** `weather_impact_duration.png`

## 3. Time-Based Mobility

**Question:** When are taxi trips slower or busier?

**Key metric:** Slowest hour: 14:00 with 18.7 min; busiest hour: 18:00.

**Insight:** Time of day is a strong operational signal for expected delay and demand.

**Why it matters:** Travelers and dispatchers can use this to plan around slower windows.

**Suggested chart:** `hourly_mobility.png`

## 4. Common Travel Corridors

**Question:** Which pickup-dropoff pairs appear most often?

**Key metric:** Top route: Upper East Side South -> Upper East Side North with 701 trips in the sample.

**Insight:** Taxi demand is concentrated in repeated corridors rather than evenly spread across the city.

**Why it matters:** These corridors are useful for demand planning, fleet positioning, and map storytelling.

**Suggested chart:** `top_zone_pairs.png`

## 5. Airport Trip Behavior

**Question:** Are airport trips different from regular city trips?

**Key metric:** Airport trips average 35.5 min and 14.1 mi; non-airport trips average 14.0 min and 2.3 mi.

**Insight:** Airport trips are a separate travel pattern, so the model should treat them as a special feature.

**Why it matters:** This improves prediction quality and gives a clear story for route planning.

**Suggested chart:** `airport_vs_non_airport.png`
