const LANGUAGE_KEY = "mazhai-language";
const DEFAULT_LANGUAGE = "en";

const TA = {
  "Mazhai AI — Tamil Nadu Rainfall Intelligence": "மழை AI — தமிழ்நாடு மழைப்பொழிவு நுண்ணறிவு",
  "WORKSPACE": "பணியிடம்", "SYSTEM": "அமைப்பு", "RAINFALL INTELLIGENCE": "மழைப்பொழிவு நுண்ணறிவு",
  "Overview": "கண்ணோட்டம்", "Live weather": "நேரடி வானிலை", "Rainfall history": "மழைப்பொழிவு வரலாறு",
  "District explorer": "மாவட்ட ஆய்வு", "Forecast & risk": "முன்னறிவிப்பு & அபாயம்",
  "Rainfall analytics": "மழைப்பொழிவு பகுப்பாய்வு", "AI assistant": "AI உதவியாளர்",
  "Data sources": "தரவு ஆதாரங்கள்", "Settings": "அமைப்புகள்", "Workspace": "பணியிடம்",
  "Refresh selected data": "தேர்ந்தெடுத்த தரவைப் புதுப்பிக்கவும்", "Refresh data": "தரவைப் புதுப்பிக்கவும்",
  "Toggle navigation": "வழிசெலுத்தலை மாற்றவும்",
  "TAMIL NADU · WEATHER DESK": "தமிழ்நாடு · வானிலை மையம்",
  "Rainfall overview": "மழைப்பொழிவு கண்ணோட்டம்", " / statewide": " / மாநிலம் முழுவதும்",
  "A grounded view of what’s happening now and what may come next.": "தற்போதைய நிலையும் அடுத்து நிகழக்கூடியவையும் குறித்த தரவு அடிப்படையிலான பார்வை.",
  "Select district": "மாவட்டத்தைத் தேர்ந்தெடுக்கவும்", "Update view": "காட்சியைப் புதுப்பிக்கவும்",
  "District weather uses representative coordinates and gridded model data—not direct rain-gauge readings. Check official IMD alerts for safety decisions.": "மாவட்ட வானிலை பிரதிநிதி இடக்குறியீடுகள் மற்றும் கட்டமைக்கப்பட்ட மாதிரித் தரவைப் பயன்படுத்துகிறது; நேரடி மழைமானி அளவீடுகள் அல்ல. பாதுகாப்பு முடிவுகளுக்கு அதிகாரப்பூர்வ IMD எச்சரிக்கைகளைப் பார்க்கவும்.",
  "IMD advisories ↗": "IMD ஆலோசனைகள் ↗", "Current temperature": "தற்போதைய வெப்பநிலை",
  "Current precipitation": "தற்போதைய மழைப்பொழிவு", "Humidity": "ஈரப்பதம்", "Next 7 days": "அடுத்த 7 நாட்கள்",
  "Select a district to load": "தரவை ஏற்ற மாவட்டத்தைத் தேர்ந்தெடுக்கவும்",
  "Provider current-condition field": "வானிலை வழங்குநரின் தற்போதைய நிலை", "Relative humidity": "சார்பு ஈரப்பதம்",
  "Forecast total when available": "கிடைக்கும்போது முன்னறிவிப்பு மொத்தம்",
  "District weather map": "மாவட்ட வானிலை வரைபடம்", "Choose a marker to inspect a district": "மாவட்டத்தைப் பார்க்க குறியீட்டைத் தேர்ந்தெடுக்கவும்",
  "MODEL GRID": "வானிலை மாதிரி", "Higher forecast": "அதிக மழை முன்னறிவிப்பு",
  "Some forecast rain": "மழை முன்னறிவிப்பு உள்ளது", "Low / no forecast": "குறைந்த / மழையில்லா முன்னறிவிப்பு",
  "No data": "தரவு இல்லை", "7-day outlook": "7 நாள் முன்னறிவிப்பு", "Selected district": "தேர்ந்தெடுக்கப்பட்ட மாவட்டம்",
  "Full forecast ↗": "முழு முன்னறிவிப்பு ↗", "Choose a district to load forecast data.": "முன்னறிவிப்புத் தரவை ஏற்ற மாவட்டத்தைத் தேர்ந்தெடுக்கவும்.",
  "Waiting for provider data": "வழங்குநர் தரவுக்காகக் காத்திருக்கிறது",
  "Recent rainfall history": "சமீபத்திய மழைப்பொழிவு வரலாறு", "Daily precipitation · selected district": "தினசரி மழைப்பொழிவு · தேர்ந்தெடுக்கப்பட்ட மாவட்டம்",
  "mm / day": "மிமீ / நாள்", "Load historical data to see the trend.": "போக்கைப் பார்க்க வரலாற்றுத் தரவை ஏற்றவும்.",
  "Rainfall signal": "மழைப்பொழிவு குறியீடு", "Evidence from the current provider forecast": "தற்போதைய வானிலை முன்னறிவிப்பிலிருந்து கிடைத்த ஆதாரம்",
  "Insights appear when forecast data is available.": "முன்னறிவிப்புத் தரவு கிடைக்கும்போது தகவல்கள் தோன்றும்.",
  "Ask the AI assistant": "AI உதவியாளரிடம் கேளுங்கள்",
  "Mazhai AI is an analytical aid, not an official warning system. Data source and retrieval time are shown with each result.": "மழை AI ஒரு பகுப்பாய்வுக் கருவி மட்டுமே; அதிகாரப்பூர்வ எச்சரிக்கை அமைப்பு அல்ல. ஒவ்வொரு முடிவிலும் தரவு ஆதாரமும் பெறப்பட்ட நேரமும் காட்டப்படும்.",
  "OBSERVATIONS": "கவனிப்புகள்", "Current conditions from the selected weather provider.": "தேர்ந்தெடுக்கப்பட்ட வானிலை வழங்குநரின் தற்போதைய நிலை.",
  "District": "மாவட்டம்", "Refresh conditions ↻": "நிலையைப் புதுப்பிக்கவும் ↻",
  "Choose a district and load its forecast.": "மாவட்டத்தைத் தேர்ந்தெடுத்து முன்னறிவிப்பை ஏற்றவும்.",
  "OBSERVED PATTERNS": "கவனிக்கப்பட்ட போக்குகள்",
  "Daily historical precipitation from gridded reanalysis data.": "கட்டமைக்கப்பட்ட மறுபகுப்பாய்வுத் தரவிலிருந்து தினசரி வரலாற்று மழைப்பொழிவு.",
  "Start date": "தொடக்க தேதி", "End date": "முடிவு தேதி", "Load history ↗": "வரலாற்றை ஏற்றவும் ↗",
  "Daily precipitation": "தினசரி மழைப்பொழிவு", "Choose a date range": "தேதி வரம்பைத் தேர்ந்தெடுக்கவும்",
  "Export CSV ↓": "CSV ஏற்றுமதி ↓", "No data loaded yet.": "இதுவரை தரவு ஏற்றப்படவில்லை.",
  "GEOGRAPHIC DIRECTORY": "புவியியல் அடைவு",
  "Explore the 38 districts and inspect available weather coverage.": "38 மாவட்டங்களை ஆராய்ந்து கிடைக்கும் வானிலைத் தரவைப் பார்க்கவும்.",
  "Search districts…": "மாவட்டங்களைத் தேடவும்…", "Search districts": "மாவட்டங்களைத் தேடவும்",
  "38 districts": "38 மாவட்டங்கள்", "Representative coordinates · station coverage varies": "பிரதிநிதி இடக்குறியீடுகள் · நிலையத் தரவு கிடைப்பது மாறலாம்",
  "FORWARD LOOK": "எதிர்நோக்கு",
  "Provider forecasts, recent accumulation context, and transparent limitations.": "வழங்குநர் முன்னறிவிப்புகள், சமீபத்திய மழைச் சேர்க்கை மற்றும் தரவு வரம்புகள்.",
  "Refresh forecast ↻": "முன்னறிவிப்பைப் புதுப்பிக்கவும் ↻",
  "Select a district to inspect its forecast.": "முன்னறிவிப்பைப் பார்க்க மாவட்டத்தைத் தேர்ந்தெடுக்கவும்.",
  "Risk interpretation": "அபாய விளக்கம்",
  "This release does not issue flood forecasts or official warnings. Rainfall totals alone are not sufficient to infer flooding. Check current IMD advisories and local disaster-management instructions.": "இந்தப் பதிப்பு வெள்ள முன்னறிவிப்புகளையோ அதிகாரப்பூர்வ எச்சரிக்கைகளையோ வழங்காது. மழை அளவு மட்டும் வெள்ளத்தைத் தீர்மானிக்கப் போதாது. தற்போதைய IMD ஆலோசனைகளையும் உள்ளூர் பேரிடர் மேலாண்மை அறிவுறுத்தல்களையும் பார்க்கவும்.",
  "Open IMD official weather service ↗": "அதிகாரப்பூர்வ IMD வானிலை சேவையைத் திறக்கவும் ↗",
  "PATTERNS & COMPARISONS": "போக்குகள் & ஒப்பீடுகள்",
  "Compare grid-based precipitation estimates across district reference points.": "மாவட்டப் பிரதிநிதி இடங்களில் கணிக்கப்பட்ட மழைப்பொழிவை ஒப்பிடவும்.",
  "Compare districts ↗": "மாவட்டங்களை ஒப்பிடவும் ↗", "District comparison": "மாவட்ட ஒப்பீடு",
  "Totals for selected period · mm": "தேர்ந்தெடுத்த காலத்திற்கான மொத்தம் · மிமீ",
  "Choose a date range and run comparison.": "தேதி வரம்பைத் தேர்ந்தெடுத்து ஒப்பீட்டைத் தொடங்கவும்.",
  "EVIDENCE-GROUNDED ANALYSIS": "ஆதார அடிப்படையிலான பகுப்பாய்வு",
  "AI weather assistant": "AI வானிலை உதவியாளர்",
  "Ask about forecasts and historical patterns. Answers use retrieved evidence when available.": "முன்னறிவிப்புகள் மற்றும் வரலாற்றுப் போக்குகளைப் பற்றி கேளுங்கள். கிடைக்கும்போது பெறப்பட்ட ஆதாரங்களைப் பயன்படுத்தி பதிலளிக்கும்.",
  "Mazhai intelligence": "மழை நுண்ணறிவு", "Checking Mistral configuration when you ask": "நீங்கள் கேட்கும்போது Mistral அமைப்பைச் சரிபார்க்கும்",
  "MISTRAL AI": "MISTRAL AI", "Vanakkam! I’m Mazhai AI.": "வணக்கம்! நான் மழை AI.",
  "I can explain retrieved forecasts and historical precipitation data. Select a district and ask a question. If the AI key is not configured, I’ll tell you rather than invent an answer.": "பெறப்பட்ட வானிலை முன்னறிவிப்புகளையும் வரலாற்று மழைப்பொழிவுத் தரவையும் விளக்க முடியும். ஒரு மாவட்டத்தைத் தேர்ந்தெடுத்து கேள்வி கேளுங்கள். AI சாவி அமைக்கப்படவில்லை என்றால், பதிலை உருவாக்கிக் கூறாமல் அதைத் தெரிவிப்பேன்.",
  "Summarize this forecast": "இந்த முன்னறிவிப்பைச் சுருக்கவும்", "Forecast vs history": "முன்னறிவிப்பு vs வரலாறு",
  "What data is missing?": "என்ன தரவு இல்லை?", "Ask Mazhai AI": "மழை AI-யிடம் கேளுங்கள்",
  "Ask about rainfall patterns, forecasts, or uncertainty…": "மழைப்பொழிவு போக்குகள், முன்னறிவிப்புகள் அல்லது நிச்சயமின்மை பற்றி கேளுங்கள்…",
  "Send question": "கேள்வியை அனுப்பவும்",
  "AI-generated explanations can be incomplete. Verify safety decisions with official authorities.": "AI உருவாக்கும் விளக்கங்கள் முழுமையற்றதாக இருக்கலாம். பாதுகாப்பு முடிவுகளை அதிகாரப்பூர்வ அமைப்புகளிடம் சரிபார்க்கவும்.",
  "Analysis context": "பகுப்பாய்வுச் சூழல்", "Responses are grounded in data retrieved by this application.": "இந்தப் பயன்பாடு பெற்ற தரவின் அடிப்படையிலேயே பதில்கள் வழங்கப்படுகின்றன.",
  "Weather source": "வானிலை ஆதாரம்", "Historical source": "வரலாற்று ஆதாரம்", "Official warnings": "அதிகாரப்பூர்வ எச்சரிக்கைகள்",
  "Not integrated": "இணைக்கப்படவில்லை",
  "Mistral is used to explain evidence, not to generate numerical weather forecasts independently.": "ஆதாரங்களை விளக்குவதற்கே Mistral பயன்படுகிறது; தனியாக எண்ணியல் வானிலை முன்னறிவிப்புகளை உருவாக்காது.",
  "PROVENANCE & FRESHNESS": "ஆதாரத் தோற்றம் & புதுப்பிப்பு",
  "Configured providers, coverage limitations, and local ingestion status.": "அமைக்கப்பட்ட வழங்குநர்கள், தரவுக் கவரேஜ் வரம்புகள் மற்றும் உள்ளூர் தரவு நிலை.",
  "Refresh status ↻": "நிலையைப் புதுப்பிக்கவும் ↻", "Stored historical data": "சேமிக்கப்பட்ட வரலாற்றுத் தரவு",
  "Records are persisted locally after successful retrieval.": "வெற்றிகரமாகப் பெறப்பட்ட பதிவுகள் உள்ளூரில் சேமிக்கப்படும்.",
  "PREFERENCES": "விருப்பங்கள்", "Configure this browser’s display preferences.": "இந்த உலாவியின் காட்சி விருப்பங்களை அமைக்கவும்.",
  "Default district": "இயல்புநிலை மாவட்டம்", "District loaded when you open the application.": "பயன்பாட்டைத் திறக்கும்போது ஏற்றப்படும் மாவட்டம்.",
  "Language": "மொழி", "Choose the display language for the application and AI assistant.": "பயன்பாடு மற்றும் AI உதவியாளருக்கான காட்சி மொழியைத் தேர்ந்தெடுக்கவும்.",
  "Units": "அலகுகள்", "Rainfall is shown in millimeters and temperature in Celsius.": "மழைப்பொழிவு மில்லிமீட்டரிலும் வெப்பநிலை செல்சியஸிலும் காட்டப்படும்.",
  "Data refresh": "தரவு புதுப்பிப்பு", "Weather responses are cached briefly to limit upstream requests.": "வானிலைப் பதில்கள் மேல்நிலை கோரிக்கைகளைக் குறைக்கச் சிறிது நேரம் தேக்கப்படும்.",
  "Theme": "தீம்", "Current theme is designed for low-glare monitoring.": "குறைந்த ஒளிச்சிதறலுடன் கண்காணிக்க தற்போதைய தீம் வடிவமைக்கப்பட்டுள்ளது.",
  "Save preferences": "விருப்பங்களைச் சேமிக்கவும்", "Preferences saved in this browser.": "இந்த உலாவியில் விருப்பங்கள் சேமிக்கப்பட்டன.",
  "Preferences saved.": "விருப்பங்கள் சேமிக்கப்பட்டன.",
  "Data services": "தரவு சேவைகள்",
  "Provider reachable": "வழங்குநரை அணுக முடிகிறது",
  "No current forecast data is available.": "தற்போதைய முன்னறிவிப்புத் தரவு இல்லை.",
  "Mistral AI is not configured. Set MISTRAL_API_KEY in the backend environment to enable evidence-grounded analysis.": "ஆதார அடிப்படையிலான பகுப்பாய்வை இயக்க backend சூழலில் MISTRAL_API_KEY அமைக்கவும்.",
  "Mistral returned an empty answer. Please try rephrasing your question.": "Mistral பதில் வழங்கவில்லை. உங்கள் கேள்வியை வேறு விதமாகக் கேட்டு முயற்சிக்கவும்.",
  "Could not reach Mistral (network or timeout). Weather and history features remain available.": "Mistral சேவையை அணுக முடியவில்லை. வானிலை மற்றும் வரலாற்று அம்சங்கள் தொடர்ந்து கிடைக்கும்.",
  "Choose both a start and end date.": "தொடக்க மற்றும் முடிவு தேதிகளை இரண்டையும் தேர்ந்தெடுக்கவும்.",
  "End date must be on or after start date.": "முடிவு தேதி தொடக்க தேதிக்கு சமமாகவோ அதற்குப் பிறகோ இருக்க வேண்டும்.",
  "Loading historical data…": "வரலாற்றுத் தரவு ஏற்றப்படுகிறது…", "No verified data available for this selection.": "இந்தத் தேர்வுக்கு சரிபார்க்கப்பட்ட தரவு இல்லை.",
  "Load history before exporting.": "ஏற்றுமதி செய்வதற்கு முன் வரலாற்றை ஏற்றவும்.", "Choose a valid date range.": "சரியான தேதி வரம்பைத் தேர்ந்தெடுக்கவும்.",
  "Retrieving data…": "தரவு பெறப்படுகிறது…", "No matching district.": "பொருந்தும் மாவட்டம் இல்லை.",
  "Loading provider conditions…": "வழங்குநரின் வானிலை நிலை ஏற்றப்படுகிறது…",
  "Provider returned no daily forecast values.": "வழங்குநர் தினசரி முன்னறிவிப்பு மதிப்புகளை வழங்கவில்லை.",
  "No current forecast data is available. The app will not generate a synthetic signal.": "தற்போதைய முன்னறிவிப்புத் தரவு இல்லை. பயன்பாடு கற்பனையான குறியீட்டை உருவாக்காது.",
  "What this means": "இதன் பொருள்", "Loading forecast…": "முன்னறிவிப்பு ஏற்றப்படுகிறது…",
  "Total precipitation": "மொத்த மழைப்பொழிவு", "Wet days (≥1 mm)": "மழை நாட்கள் (≥1 மிமீ)",
  "Daily maximum": "தினசரி அதிகபட்சம்", "Valid daily values": "செல்லுபடியாகும் தினசரி மதிப்புகள்",
  "District totals": "மாவட்ட மொத்தங்கள்", "Sorted by returned precipitation total": "பெறப்பட்ட மழைப்பொழிவு மொத்தத்தின்படி வரிசைப்படுத்தப்பட்டது",
  "Total (mm)": "மொத்தம் (மிமீ)", "Valid days": "செல்லுபடியாகும் நாட்கள்", "Status": "நிலை",
  "Retrieved": "பெறப்பட்டது", "Unavailable": "கிடைக்கவில்லை", "Retry": "மீண்டும் முயற்சிக்கவும்",
  "7-day precipitation": "7 நாள் மழைப்பொழிவு",
  "Rainfall timing": "மழைப்பொழிவு நேரம்",
  "Air temperature · Celsius": "காற்றின் வெப்பநிலை · செல்சியஸ்",
  "Atmospheric conditions": "வளிமண்டல நிலைகள்",
  "Data provenance": "தரவு ஆதாரம்",
  "Provider and retrieval metadata": "வழங்குநர் மற்றும் தரவு பெறப்பட்ட விவரங்கள்",
  "Source": "ஆதாரம்",
  "Retrieved at": "பெறப்பட்ட நேரம்",
  "Data status": "தரவு நிலை",
  "Coordinate type": "இடக்குறியீட்டு வகை",
  "District reference point": "மாவட்டப் பிரதிநிதி இடம்",
  "Weather loads on selection": "தேர்ந்தெடுத்தால் வானிலை ஏற்றப்படும்",
  "Provider forecast · representative district coordinates": "வழங்குநர் முன்னறிவிப்பு · மாவட்டப் பிரதிநிதி இடக்குறியீடுகள்",
  "Today": "இன்று",
  "Probability not provided": "மழை நிகழ்தகவு தரப்படவில்லை",
  "Open-Meteo model data · representative coordinates": "Open-Meteo மாதிரித் தரவு · மாவட்டப் பிரதிநிதி இடக்குறியீடுகள்",
  "Explore district": "மாவட்டத்தை ஆராயவும்",
  "Stale cache": "காலாவதியான தேக்கத் தரவு",
  "Cached": "தேக்கத் தரவு",
  "Fresh response": "புதிய பதில்",
  "cached/stale": "தேக்கப்பட்டது / காலாவதியானது",
  "cached": "தேக்கப்பட்டது",
  "retrieved": "பெறப்பட்டது",
  "Historical grid/reanalysis estimate, not direct station observation.": "வரலாற்று கட்டமைக்கப்பட்ட மறுபகுப்பாய்வு மதிப்பீடு; நேரடி நிலைய அளவீடு அல்ல.",
  "7-day sum is a model output, not a warning": "7 நாள் மொத்தம் மாதிரி முடிவு மட்டுமே; எச்சரிக்கை அல்ல.",
  "Rainfall totals are model estimates, not direct station readings.": "மழைப்பொழிவு மொத்தங்கள் மாதிரி மதிப்பீடுகள்; நேரடி நிலைய அளவீடுகள் அல்ல.",
  "APP INDICATOR · NOT OFFICIAL": "பயன்பாட்டு குறியீடு · அதிகாரப்பூர்வமல்ல",
  "Preliminary forecast screening only. This is not an IMD warning or a flood prediction.": "முன்னறிவிப்பின் ஆரம்ப நிலைத் திரையிடல் மட்டுமே. இது IMD எச்சரிக்கையோ வெள்ள முன்னறிவிப்போ அல்ல.",
  "The available evidence could not determine an attention level.": "கிடைத்த ஆதாரங்களால் கவனநிலையைத் தீர்மானிக்க முடியவில்லை.",
  "Source unavailable": "ஆதாரம் கிடைக்கவில்லை",
  "Rainfall attention": "மழைப்பொழிவு கவனநிலை", "Current conditions and forecast": "தற்போதைய நிலை மற்றும் முன்னறிவிப்பு",
  "Historical context": "வரலாற்றுப் பின்னணி", "What to watch next": "அடுத்து கவனிக்க வேண்டியவை",
  "Recommended actions": "பரிந்துரைக்கப்படும் நடவடிக்கைகள்", "Confidence and limitations": "நம்பகத்தன்மை மற்றும் வரம்புகள்",
  "Checking retrieved evidence…": "பெறப்பட்ட ஆதாரங்களைச் சரிபார்க்கிறது…", "The assistant returned no answer.": "உதவியாளர் பதில் வழங்கவில்லை.",
  "The request took too long. Please try again.": "கோரிக்கை முடிவடைய அதிக நேரம் எடுத்தது. மீண்டும் முயற்சிக்கவும்.",
  "Refresh complete.": "புதுப்பிப்பு முடிந்தது.", "Dashboard updated.": "டாஷ்போர்டு புதுப்பிக்கப்பட்டது.",
  "India": "இந்தியா",
  "Tamil Nadu": "தமிழ்நாடு",
  "Ariyalur": "அரியலூர்",
  "Chengalpattu": "செங்கல்பட்டு",
  "Chennai": "சென்னை",
  "Coimbatore": "கோயம்புத்தூர்",
  "Cuddalore": "கடலூர்",
  "Dharmapuri": "தர்மபுரி",
  "Dindigul": "திண்டுக்கல்",
  "Erode": "ஈரோடு",
  "Kallakurichi": "கள்ளக்குறிச்சி",
  "Kancheepuram": "காஞ்சிபுரம்",
  "Kanniyakumari": "கன்னியாகுமரி",
  "Karur": "கரூர்",
  "Krishnagiri": "கிருஷ்ணகிரி",
  "Madurai": "மதுரை",
  "Mayiladuthurai": "மயிலாடுதுறை",
  "Nagapattinam": "நாகப்பட்டினம்",
  "Namakkal": "நாமக்கல்",
  "The Nilgiris": "நீலகிரி",
  "Perambalur": "பெரம்பலூர்",
  "Pudukkottai": "புதுக்கோட்டை",
  "Ramanathapuram": "இராமநாதபுரம்",
  "Ranipet": "ராணிப்பேட்டை",
  "Salem": "சேலம்",
  "Sivaganga": "சிவகங்கை",
  "Tenkasi": "தென்காசி",
  "Thanjavur": "தஞ்சாவூர்",
  "Theni": "தேனி",
  "Thoothukudi": "தூத்துக்குடி",
  "Tiruchirappalli": "திருச்சிராப்பள்ளி",
  "Tirunelveli": "திருநெல்வேலி",
  "Tirupathur": "திருப்பத்தூர்",
  "Tiruppur": "திருப்பூர்",
  "Tiruvallur": "திருவள்ளூர்",
  "Tiruvannamalai": "திருவண்ணாமலை",
  "Tiruvarur": "திருவாரூர்",
  "Vellore": "வேலூர்",
  "Viluppuram": "விழுப்புரம்",
  "Virudhunagar": "விருதுநகர்",
  "API unavailable": "API கிடைக்கவில்லை"
};

const EN = Object.fromEntries(Object.entries(TA).map(([english, tamil]) => [tamil, english]));
const textSources = new WeakMap();
const attributeSources = new WeakMap();
let observer = null;
let currentLanguage = DEFAULT_LANGUAGE;

export function getLanguage() {
  try { return localStorage.getItem(LANGUAGE_KEY) === "ta" ? "ta" : "en"; }
  catch { return DEFAULT_LANGUAGE; }
}

export function setLanguage(language) {
  currentLanguage = language === "ta" ? "ta" : "en";
  try { localStorage.setItem(LANGUAGE_KEY, currentLanguage); } catch {}
  return currentLanguage;
}

export function t(english) {
  return currentLanguage === "ta" ? (TA[english] || english) : english;
}

function translatePhrase(value, language) {
  if (language === "en") return EN[value] || value;
  if (TA[value]) return TA[value];
  let match = value.match(/^(\d+)-day provider precipitation sum$/);
  if (match) return match[1] + " நாள் வானிலை முன்னறிவிப்பு மழைப்பொழிவு மொத்தம்";
  match = value.match(/^Loaded (\d+) daily records\.$/);
  if (match) return match[1] + " தினசரி பதிவுகள் ஏற்றப்பட்டன.";
  match = value.match(/^Comparison completed: (\d+)\/38 districts\.$/);
  if (match) return "ஒப்பீடு முடிந்தது: 38 மாவட்டங்களில் " + match[1] + " மாவட்டங்கள்.";
  match = value.match(/^(\d+) of (\d+) districts$/);
  if (match) return match[2] + " மாவட்டங்களில் " + match[1] + " மாவட்டங்கள்";
  match = value.match(/^(\d+) districts$/);
  if (match) return match[1] + " மாவட்டங்கள்";
  match = value.match(/^(\d+) mapped areas loaded from the configured GeoJSON\..*$/);
  if (match) return "கட்டமைக்கப்பட்ட GeoJSON-இலிருந்து " + match[1] + " வரைபடப் பகுதிகள் ஏற்றப்பட்டன.";
  match = value.match(/^(\d+(?:\.\d+)?)% chance$/);
  if (match) return match[1] + "% வாய்ப்பு";
  match = value.match(/^7-day forecast total: (.+) mm$/);
  if (match) return "7 நாள் மழை முன்னறிவிப்பு மொத்தம்: " + match[1] + " மிமீ";
  match = value.match(/^(\d+(?:\.\d+)?) mm forecast total from (.+)\. This is a model forecast, not a measured district total\.$/);
  if (match) return match[1] + " மிமீ முன்னறிவிப்பு மழை மொத்தம் (" + match[2] + "). இது மாதிரி முன்னறிவிப்பு; அளவிடப்பட்ட மாவட்ட மொத்தம் அல்ல.";
  match = value.match(/^(\d+) of (\d+) forecast days have at least 1 mm indicated\. Highest daily amount: (.+) mm on (.+)\.$/);
  if (match) return match[2] + " முன்னறிவிப்பு நாட்களில் " + match[1] + நாட்களில் குறைந்தது 1 மிமீ மழை எதிர்பார்க்கப்படுகிறது. அதிகபட்ச தினசரி அளவு " + match[3] + " மிமீ (" + match[4] + ").";
  match = value.match(/^([^·]+) · current$/);
  if (match) return match[1] + " · தற்போதைய நிலை";
  match = value.match(/^Cannot connect to Mazhai AI API: (.+)$/);
  if (match) return "மழை AI API-ஐ இணைக்க முடியவில்லை: " + match[1];
  return value;
}

function excludedTextNode(node) {
  const parent = node.parentElement;
  return !parent || !!parent.closest("script,style,textarea,code");
}

function translateTextNode(node, language) {
  if (excludedTextNode(node)) return;
  const value = node.nodeValue || "";
  const previous = textSources.get(node);
  const source = previous && value === previous.lastApplied ? previous.source : value;
  const trimmed = source.trim();
  const translated = translatePhrase(trimmed, language);
  const leading = (source.match(/^\s*/) || [""])[0];
  const trailing = (source.match(/\s*$/) || [""])[0];
  const next = leading + translated + trailing;
  textSources.set(node, { source, lastApplied: next });
  if (next !== value) node.nodeValue = next;
}

function translateAttributes(root, language) {
  const nodes = [];
  if (root && root.nodeType === 1) nodes.push(root);
  if (root && root.querySelectorAll) nodes.push(...root.querySelectorAll("*"));
  for (const node of nodes) {
    for (const attribute of ["placeholder", "aria-label", "title"]) {
      if (!node.hasAttribute(attribute)) continue;
      const value = node.getAttribute(attribute) || "";
      let saved = attributeSources.get(node);
      if (!saved) { saved = {}; attributeSources.set(node, saved); }
      const previous = saved[attribute];
      const source = previous && value === previous.lastApplied ? previous.source : value;
      const next = translatePhrase(source, language);
      saved[attribute] = { source, lastApplied: next };
      if (next !== value) node.setAttribute(attribute, next);
    }
  }
}

function walkText(root, language) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode())) translateTextNode(node, language);
}

export function applyLanguage(language = getLanguage()) {
  currentLanguage = language === "ta" ? "ta" : "en";
  document.documentElement.lang = currentLanguage;
  document.title = t("Mazhai AI — Tamil Nadu Rainfall Intelligence");
  walkText(document.body, currentLanguage);
  translateAttributes(document.body, currentLanguage);
  if (!observer && document.body) {
    observer = new MutationObserver(records => {
      for (const record of records) {
        if (record.type === "characterData") {
          translateTextNode(record.target, currentLanguage);
        } else {
          for (const node of record.addedNodes) {
            if (node.nodeType === 3) translateTextNode(node, currentLanguage);
            else if (node.nodeType === 1) {
              walkText(node, currentLanguage);
              translateAttributes(node, currentLanguage);
            }
          }
        }
      }
    });
    observer.observe(document.body, { subtree: true, childList: true, characterData: true });
  }
}

export function initLanguagePreference() {
  setLanguage(getLanguage());
  applyLanguage(currentLanguage);
}
