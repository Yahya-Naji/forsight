-- ============================================================
-- 029 TOPIC SEARCH QUERIES — what Lane B searches for each topic
--
-- A topic's name is written for a reader, not a search engine: "Cognitive EW"
-- reduced to the single term `cognitive`. Each live topic carries a GDELT query
-- (quoted phrases, OR groups in parentheses), used by the weekly Lane B walk
-- for every topic, alongside any questions bound to it.
-- ============================================================

alter table topics add column if not exists search_query text;

update topics t set search_query = q.query from (values
  ('EW-T10', '("electronic warfare" OR "jamming" OR "jammer") (radar OR datalink OR "electronic attack")'),
  ('EW-T11', '("directed energy" OR "high-power microwave" OR "high energy laser") (drone OR "counter-drone")'),
  ('EW-T12', '("anti-jam" OR "electronic protection" OR "frequency hopping" OR "low probability of intercept")'),
  ('EW-T13', '("electronic support" OR "signals intelligence" OR "direction finding" OR "emitter geolocation")'),
  ('EW-T14', '("GPS jamming" OR "GNSS jamming" OR "GPS spoofing" OR "GNSS spoofing" OR "GNSS interference")'),
  ('EW-T15', '("electromagnetic spectrum" OR "spectrum management" OR "spectrum deconfliction") military'),
  ('EW-T16', '("counter-drone" OR "counter-UAS") (jamming OR jammer OR "electronic warfare")'),
  ('EW-T17', '("fiber-optic drone" OR "fibre-optic drone" OR "fiber optic drone" OR "fiber-optic FPV")'),
  ('EW-T18', '("suppression of enemy air defenses" OR "SEAD mission" OR "anti-radiation missile" OR "airborne jammer")'),
  ('EW-T19', '(Shahed OR "loitering munition" OR "one-way attack drone" OR "drone swarm")'),
  ('CS-T10', '("cyber electromagnetic" OR "cyber and electronic warfare" OR "cyber-electromagnetic")'),
  ('CS-T11', '("drone takeover" OR "protocol manipulation" OR "cyber takeover") (drone OR "counter-drone")'),
  ('CS-T12', '("electronic warfare" OR "software-defined radio" OR "threat library") (cyber OR vulnerability OR firmware)'),
  ('CS-T13', '("air defense" OR "counter-drone" OR "command and control") (cyberattack OR "data integrity" OR spoofed)'),
  ('CS-T14', '("electronic warfare" OR radar OR "RF components") ("supply chain" OR counterfeit)'),
  ('AI-T10', '("cognitive electronic warfare" OR "AI electronic warfare" OR "machine learning jamming" OR "adaptive jamming")'),
  ('AI-T11', '("counter-drone" OR "counter-UAS") ("artificial intelligence" OR "machine learning")'),
  ('AI-T12', '("autonomous drone" OR "AI-guided drone" OR "AI-enabled drone" OR "drone swarm") jamming'),
  ('AI-T13', '("adversarial machine learning" OR "AI assurance" OR "test and evaluation") ("electronic warfare" OR "signal classification")'),
  ('PR-T10', '("electronic warfare" OR "threat library" OR "mission data") (reprogramming OR "data rights" OR "software update")'),
  ('PR-T11', '("electronic warfare" OR "counter-drone" OR "counter-UAS") (contract OR procurement OR acquisition)'),
  ('PR-T12', '("electronic warfare" OR "counter-drone") ("export control" OR sovereign OR "local production" OR "EDGE Group")'),
  ('PR-T13', '("electronic warfare" OR "counter-drone" OR "counter-UAS") (test OR evaluation OR trial OR exercise)'),
  ('PR-T14', '("counter-drone" OR "counter-UAS") (cost OR "cost per" OR interceptor OR magazine)')
) as q(id, query)
where t.id = q.id;
