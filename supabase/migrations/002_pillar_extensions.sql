-- ============================================================
-- 002 PILLAR EXTENSIONS — entities specific to each pillar
-- One generic 'entities' table + typed views keeps the POC light;
-- promote to real tables when a pillar's model stabilises.
-- ============================================================

create table entities (
  id text primary key,                     -- e.g. 'CS-THREAT-001'
  pillar pillar not null,
  entity_type text not null,               -- from the per-pillar catalogs below
  name text not null,
  attrs jsonb not null default '{}',
  created_at timestamptz default now()
);
create index entities_pillar_type on entities (pillar, entity_type);

-- Entity-type catalog (validated by pipeline/models.py, mirrored here for reference):
-- CYBERSECURITY: threat_actor, cyber_threat, attack_surface, defence_system,
--                control, standard, supplier_dependency, cyber_incident,
--                uae_sector, mission_assurance_requirement
-- AI:            ai_capability, ai_model, dataset_asset, tevv_gate,
--                human_control_boundary, adversarial_threat, compute_dependency
-- ELECTRONIC_WARFARE: spectrum_band, ew_capability, emitter_profile,
--                link_dependence, pnt_mode, reprogramming_right, deconfliction_constraint
-- PROCUREMENT:   acquisition_mechanism, contract_right, sovereignty_assessment,
--                industrial_capability, refresh_cycle, export_control_constraint,
--                localisation_program

-- entity <-> evidence (every entity fact must be evidenced)
create table entity_evidence (
  entity_id text references entities(id) on delete cascade,
  evidence_id text references evidence(id),
  primary key (entity_id, evidence_id)
);

-- Sovereignty levels (used by PROCUREMENT + CS supplier assessments)
create type sovereignty_level as enum ('L1_EXTERNAL','L2_LOCAL_SUSTAINMENT','L3_LOCAL_INTEGRATION','L4_SW_MISSION_DATA','L5_FULL_NATIONAL');
alter table entities add column sovereignty sovereignty_level;
