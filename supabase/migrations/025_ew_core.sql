-- ============================================================
-- 025 EW CORE — Electronic Warfare is the core pillar; the other
-- three are lenses on it.
--
-- The client's priority is Electronic Warfare. Cybersecurity, AI and
-- Procurement stay as pillars, but each of their topics now has to say which
-- EW function it affects and how. A topic that cannot name one is out of
-- scope, and the database refuses it.
--
-- ew_functions is taken from the two client manuals (docs/source/):
--   electronic-warfare-manual.pdf          EA / EP / ES, EMSO, CEMA, cognitive EW
--   cuas-operational-mechanics-manual.pdf  detect → fuse → soft/hard kill → BDA
-- The manuals carry no publisher or date, so they define the structure and are
-- never cited as evidence.
--
-- The old topics are retired rather than deleted: evidence still points at
-- them until pipeline/refile.py moves it, and a retired topic can be revived.
-- ============================================================

create table if not exists ew_functions (
  id text primary key,                  -- e.g. 'EA-JAM'
  division text not null check (division in ('EA','EP','ES','EMSO','CEMA','CUAS')),
  name text not null,
  description text not null,
  source_ref text not null              -- which manual section it came from
);

insert into ew_functions (id, division, name, description, source_ref) values
-- Electronic Attack
('EA-JAM','EA','Noise jamming',
 'Barrage, spot and sweep jamming that drives the receiver''s signal-to-noise ratio below its detection threshold.',
 'EW manual §4.1, §5'),
('EA-DEC','EA','Deception and DRFM spoofing',
 'Intercepting and re-transmitting modified signals so the receiver sees false targets, ranges or velocities.',
 'EW manual §4.1'),
('EA-GNSS','EA','GNSS jamming and spoofing',
 'Overpowering or faking satellite-navigation signals to deny or misdirect positioning.',
 'C-UAS manual §6.2'),
('EA-DEW','EA','Directed energy',
 'High-power microwave and high-energy laser effects against electronics, sensors and airframes.',
 'EW manual §4.1; C-UAS manual §7.1'),
('EA-ARM','EA','Anti-radiation weapons',
 'Passive RF seekers that home on an emitting radar.',
 'EW manual §4.1'),
('EA-SEAD','EA','Suppression of air defences',
 'Stand-off and escort jamming against integrated air-defence radars and command posts.',
 'EW manual §5.2'),
-- Electronic Protection
('EP-LPI','EP','Low probability of intercept',
 'Spread spectrum, fast frequency hopping and power management that keep friendly emissions below an adversary''s noise floor.',
 'EW manual §4.2'),
('EP-EMCON','EP','Emissions control',
 'Restricting friendly transmissions so hostile Electronic Support cannot locate them.',
 'EW manual §4.2'),
('EP-ANTIJAM','EP','Anti-jam processing',
 'Sidelobe blanking, nulling and receiver techniques that reject jamming.',
 'EW manual §4.2'),
('EP-PNT','EP','Resilient navigation and timing',
 'Keeping friendly positioning and timing usable when GNSS is jammed or spoofed.',
 'EW manual §4 (EP definition); C-UAS manual §6.2'),
-- Electronic Support
('ES-INTERCEPT','ES','Signal intercept and classification',
 'Searching for, intercepting and identifying radiated emissions for real-time threat recognition.',
 'EW manual §4.3; C-UAS manual §4.1'),
('ES-DF','ES','Direction finding and geolocation',
 'Locating emitters passively by angle, time difference or frequency difference of arrival.',
 'EW manual §6.1'),
('ES-WARN','ES','Threat warning',
 'Immediate warning of hostile emitters to the tactical commander, as distinct from strategic SIGINT.',
 'EW manual §4.3'),
-- Spectrum operations
('EMSO-BANDS','EMSO','Band use and propagation',
 'How HF to EHF and optical bands are used, and what each is exposed to.',
 'EW manual §2'),
('EMSO-DECON','EMSO','Spectrum congestion and deconfliction',
 'Operating many friendly emitters without interfering with each other in congested or contested spectrum.',
 'EW manual §1, §2'),
-- Convergence and next generation
('CEMA-RFCYBER','CEMA','Cyber intrusion over RF',
 'Using the RF path into a receiving antenna as an entry point for cyber payloads, bypassing air gaps.',
 'EW manual §9'),
('CEMA-COG','CEMA','Cognitive EW',
 'Machine learning that classifies unseen waveforms and adapts countermeasures in real time.',
 'EW manual §8'),
('CEMA-SDR','CEMA','Software-defined EW',
 'Software-defined radios and AESA arrays: EW capability that changes through software and threat-library updates.',
 'EW manual §8'),
-- The counter-UAS engagement chain
('CUAS-DETECT','CUAS','Detection',
 'RF sensing, micro-Doppler radar, EO/IR and acoustic detection of small uncrewed aircraft.',
 'C-UAS manual §4'),
('CUAS-FUSE','CUAS','Fusion, classification and engagement decision',
 'Track correlation, AI classification, threat scoring and rules-of-engagement logic, with the human in or on the loop.',
 'C-UAS manual §5'),
('CUAS-SOFT','CUAS','Soft-kill',
 'RF jamming, GNSS disruption and protocol takeover that defeat a drone without destroying it.',
 'C-UAS manual §6'),
('CUAS-HARD','CUAS','Hard-kill',
 'Directed energy, interceptor drones and guided or airburst munitions.',
 'C-UAS manual §7'),
('CUAS-BDA','CUAS','Kill assessment',
 'Confirming the threat is defeated, or re-engaging with another layer.',
 'C-UAS manual §8')
on conflict (id) do update set division = excluded.division, name = excluded.name,
  description = excluded.description, source_ref = excluded.source_ref;

-- ---------- topics: the EW link, and retirement ----------
alter table topics add column if not exists ew_functions text[] not null default '{}';
alter table topics add column if not exists ew_impact text;
alter table topics add column if not exists retired_at timestamptz;

-- Arrays cannot carry a foreign key, so the trigger does it.
create or replace function topics_check_ew_functions() returns trigger
language plpgsql as $$
declare bad text;
begin
  select f into bad from unnest(new.ew_functions) f
   where not exists (select 1 from ew_functions e where e.id = f) limit 1;
  if bad is not null then
    raise exception 'topic %: unknown EW function %', new.id, bad;
  end if;
  return new;
end $$;

drop trigger if exists topics_ew_functions_fk on topics;
create trigger topics_ew_functions_fk before insert or update of ew_functions on topics
  for each row execute function topics_check_ew_functions();

-- ---------- evidence: archive instead of delete ----------
-- Set only by `refile.py --apply` from a reviewed file. Null means live.
alter table evidence add column if not exists archived_at timestamptz;
alter table evidence add column if not exists archived_reason text;

-- ---------- the new topics ----------
-- Numbered from T10 so they never reuse an old id with a new meaning, and so
-- the console's "-T##" id scheme keeps working.
insert into topics (id, pillar, name, description, uae_relevance, ew_functions, ew_impact) values
-- Electronic Warfare: the core
('EW-T10','ELECTRONIC_WARFARE','Electronic attack: jamming and deception',
 'Noise jamming, DRFM deception and spoofing against radars, datalinks and seekers; how techniques and their counters are moving.',
 'Sets what UAE electronic attack can still deny, and against which emitters.',
 '{EA-JAM,EA-DEC}', null),
('EW-T11','ELECTRONIC_WARFARE','Directed energy and hard-kill electronic effects',
 'High-power microwave and laser effects, their maturity, cost per engagement and limits.',
 'Determines whether one-to-many defeat is affordable against saturation attacks.',
 '{EA-DEW,CUAS-HARD}', null),
('EW-T12','ELECTRONIC_WARFARE','Electronic protection and anti-jam resilience',
 'Low-probability-of-intercept links, emissions control and anti-jam processing for friendly sensors and communications.',
 'Decides whether UAE systems keep working when an adversary jams them.',
 '{EP-LPI,EP-EMCON,EP-ANTIJAM}', null),
('EW-T13','ELECTRONIC_WARFARE','Electronic support: intercept, direction finding and warning',
 'Intercepting, classifying and locating emitters, and warning commanders in time to act.',
 'Detection and cueing depend on finding the emitter first.',
 '{ES-INTERCEPT,ES-DF,ES-WARN}', null),
('EW-T14','ELECTRONIC_WARFARE','GNSS denial and resilient navigation',
 'GNSS jamming and spoofing as both a threat and a defensive effect, and the alternatives to satellite navigation.',
 'Satellite-navigation interference is a regional reality and cuts both ways.',
 '{EA-GNSS,EP-PNT}', null),
('EW-T15','ELECTRONIC_WARFARE','Spectrum congestion and deconfliction',
 'Operating many friendly emitters in congested or contested spectrum without interfering with each other.',
 'Dense, layered defences around high-value sites multiply friendly emitters.',
 '{EMSO-DECON,EMSO-BANDS}', null),
('EW-T16','ELECTRONIC_WARFARE','Counter-UAS through the spectrum',
 'RF detection and RF or GNSS soft-kill of uncrewed aircraft, and how well it still covers the threat.',
 'Drones are the threat most likely to test UAE spectrum defences.',
 '{CUAS-DETECT,CUAS-SOFT,ES-DF}', null),
('EW-T17','ELECTRONIC_WARFARE','Link-independent and low-emission threats',
 'Fibre-optic control, autonomous continuation and low-emission platforms that give RF sensing and jamming nothing to work on.',
 'Shrinks the share of the threat that RF-based defence can see or defeat.',
 '{CUAS-DETECT,ES-INTERCEPT,CUAS-SOFT}', null),
('EW-T18','ELECTRONIC_WARFARE','Suppression of air defences',
 'Stand-off and escort jamming, decoys and anti-radiation weapons used against integrated air defence.',
 'UAE air defence is the target of these techniques.',
 '{EA-SEAD,EA-ARM}', null),
('EW-T19','ELECTRONIC_WARFARE','The uncrewed threat EW must defeat',
 'How drones and loitering munitions are changing in size, range, speed, payload, numbers and control, by NATO class (Groups 1 to 5).',
 'Sets what UAE sensors must detect and what UAE effectors must defeat.',
 '{CUAS-DETECT,CUAS-SOFT,CUAS-HARD}', null),
-- Cybersecurity → EW
('CS-T10','CYBERSECURITY','Cyber intrusion over RF',
 'Delivering cyber payloads through the radio path into receivers, datalinks and sensors.',
 'Air-gapped defence networks are reachable through their antennas.',
 '{CEMA-RFCYBER,ES-INTERCEPT}',
 'Turns every receiving antenna into a network entry point, so EW and cyber defence have to be planned together.'),
('CS-T11','CYBERSECURITY','Protocol takeover as a counter-UAS effect',
 'Cyber takeover of drone control protocols to land or redirect them instead of jamming them.',
 'Lets a drone be captured intact near sensitive sites without wide-area jamming.',
 '{CUAS-SOFT}',
 'Moves part of soft-kill from the EW layer into the cyber layer, with less collateral interference than jamming.'),
('CS-T12','CYBERSECURITY','Cyber attack surface of software-defined EW',
 'Firmware, threat-library, mission-data and update channels of software-defined EW and counter-UAS systems.',
 'Foreign-supported EW systems take updates through channels the UAE does not fully control.',
 '{CEMA-SDR,CEMA-COG}',
 'An EW system that changes through software can be compromised through software: a poisoned threat library blinds it.'),
('CS-T13','CYBERSECURITY','Integrity of fusion and C2 tracks',
 'Manipulation of track, identity or engagement data between sensors, fusion and effectors.',
 'Layered air defence relies on one shared picture.',
 '{CUAS-FUSE}',
 'A falsified track sends EW and kinetic effectors at the wrong target or none, without any jamming.'),
('CS-T14','CYBERSECURITY','Supply-chain integrity of EW electronics',
 'Provenance and tampering risk in the RF components, processors and firmware inside EW systems.',
 'Most EW hardware is imported.',
 '{CEMA-SDR,EP-ANTIJAM}',
 'Compromised components can disable or betray an EW system before it is ever switched on.'),
-- AI → EW
('AI-T10','AI','Cognitive EW',
 'Machine learning that classifies unseen waveforms and adapts jamming or protection in real time.',
 'Threats that change waveform faster than a library update favour adaptive EW.',
 '{CEMA-COG,ES-INTERCEPT,EA-JAM}',
 'Shortens the loop from intercepting a new signal to countering it from weeks to seconds.'),
('AI-T11','AI','AI in counter-UAS fusion and engagement decisions',
 'AI track correlation, classification and threat scoring, and where the human stays in or on the loop.',
 'Decides how fast UAE defences can respond and who authorises the effect.',
 '{CUAS-FUSE,CUAS-DETECT}',
 'Decides which electronic or kinetic effect is chosen and how fast, inside a window of seconds.'),
('AI-T12','AI','Hostile autonomy against spectrum-based defence',
 'Autonomous navigation, terminal guidance and swarming that remove the control link and GNSS dependence EW exploits.',
 'Compresses UAE decision windows and weakens RF assumptions.',
 '{CUAS-SOFT,EA-GNSS,ES-INTERCEPT}',
 'An autonomous drone has no link to jam and needs no GNSS, so EW soft-kill stops working against it.'),
('AI-T13','AI','Assurance of AI in EW functions',
 'Testing, adversarial robustness and revalidation of AI used to classify signals or recommend effects.',
 'Evidence is needed before an AI EW function is trusted operationally.',
 '{CEMA-COG,CUAS-FUSE}',
 'An adversary who fools the classifier defeats the EW system without touching its RF hardware.'),
-- Procurement → EW
('PR-T10','PROCUREMENT','Reprogramming and mission-data rights',
 'Rights to update threat libraries, mission data, waveforms and software on acquired EW systems.',
 'Without these rights the UAE cannot adapt its EW at operational speed.',
 '{CEMA-SDR,CEMA-COG,ES-INTERCEPT}',
 'Determines whether a new threat signal can be countered locally or must wait on a foreign supplier.'),
('PR-T11','PROCUREMENT','Acquiring software-defined EW at threat speed',
 'Spiral, modular and framework acquisition for EW and counter-UAS capability that changes faster than the procurement cycle.',
 'Conventional cycles lag the threat in the layers that change fastest.',
 '{CEMA-SDR,CUAS-SOFT}',
 'Decides whether fielded EW matches this year''s threat or one from several years ago.'),
('PR-T12','PROCUREMENT','EW sovereignty and export controls',
 'Which EW functions require national control, and how export licensing constrains access, upgrades and support.',
 'EW is among the most export-controlled capability areas.',
 '{ES-INTERCEPT,EA-JAM,CEMA-SDR}',
 'Sets which EW functions the UAE can operate, modify and sustain on its own in a crisis.'),
('PR-T13','PROCUREMENT','Test evidence under UAE spectrum conditions',
 'The test and evaluation evidence required before accepting EW and counter-UAS systems.',
 'Performance elsewhere does not transfer automatically to the Gulf spectrum and climate.',
 '{EMSO-DECON,EMSO-BANDS,CUAS-DETECT}',
 'Proves an EW capability works in the UAE''s own spectrum before it is relied on.'),
('PR-T14','PROCUREMENT','Effector economics in counter-UAS',
 'Cost per engagement and magazine depth of jamming, directed energy and kinetic effectors against cheap drones.',
 'Saturation attacks make cost per defeat a strategic constraint.',
 '{CUAS-SOFT,CUAS-HARD,EA-DEW}',
 'Decides how much of the defence rests on EW and directed energy rather than expensive interceptors.')
on conflict (id) do update set pillar = excluded.pillar, name = excluded.name,
  description = excluded.description, uae_relevance = excluded.uae_relevance,
  ew_functions = excluded.ew_functions, ew_impact = excluded.ew_impact, retired_at = null;

-- ---------- retire every topic that is not EW-linked ----------
update topics set retired_at = now()
 where retired_at is null and cardinality(ew_functions) = 0;

-- Added only now: the old topics had to be retired first.
-- Every live topic names at least one EW function; outside the EW pillar it
-- must also say, in one sentence, what it does to EW.
alter table topics drop constraint if exists topics_ew_link;
alter table topics add constraint topics_ew_link check (
  retired_at is not null
  or (cardinality(ew_functions) > 0
      and (pillar = 'ELECTRONIC_WARFARE' or nullif(trim(ew_impact), '') is not null))
);

-- ---------- re-point the question bank ----------
-- Questions on a topic with a clear successor follow it. The rest stay on
-- their retired topic and are no longer asked (lane_b skips them).
update questions q set topic_id = m.new_id
  from (values ('EW-T01','EW-T16'), ('EW-T02','EW-T15'),
               ('AI-T01','AI-T11'), ('AI-T02','AI-T12'),
               ('PR-T01','PR-T11'), ('PR-T02','PR-T12'),
               ('CS-T08','CS-T12'), ('CS-T02','CS-T12'),
               ('CS-T03','CS-T14'), ('CS-T04','CS-T12')) as m(old_id, new_id)
 where q.topic_id = m.old_id;

-- ---------- read access ----------
alter table ew_functions enable row level security;
drop policy if exists ew_functions_anon_read on ew_functions;
create policy ew_functions_anon_read on ew_functions for select to anon using (true);
