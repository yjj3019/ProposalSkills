# Content pattern bank (content-patterns)

These are **body-content skeletons** repeatedly validated across winning proposals. They describe what belongs
inside a page, rather than the outline. Every pattern is anonymized/generalized; fill figures/items with project-specific facts
(same rule as phrase-library: never fabricate empty slots).

## 1. Seven project-management areas (types A/B — management chapter)

Conventionally present 7 areas + a 3-stage process:

| # | Area | Main management items |
|---|---|---|
| 1 | Progress | Check/report progress, manage schedule adherence targets |
| 2 | Risk | Respond to changing project conditions and differing site conditions |
| 3 | Quality | Quality assurance measures linked to process control |
| 4 | Communication | Inter-organizational communication and dispute mediation |
| 5 | Resources | Optimize technical staffing, respond to resource risks |
| 6 | Security | Personnel and document security measures |
| 7 | Documents/deliverables | Manage deliverables by delivery stage |

Three stages: **Initiation** (site analysis, coordination system, schedule/delivery plan) →
**Execution/control** (monitoring, control, progress, requirement changes) →
**Closure** (stable-operation support, emergency drills, completion report).

## 2. Preventive inspection checklist (type B — incident prevention)

Use two layers. The checklist must have 4 columns: `Inspection item | Method | Content | Criterion (threshold)`.

- **OS layer**: host information/OS release/kernel; CPU (example: Idle at least 40%),
  memory (example: below 80%), disk (below 80% per partition), processes, filesystem state,
  system logs, network (NIC/bond redundancy/time synchronization), Uptime (example: under 180 days recommended).
  Actual commands in the method column establish credibility.
- **Platform/cluster layer**: version, node Active status, key infrastructure component status,
  spare storage (threshold), **remaining certificate validity (example: warning below 3 months)**,
  event logs, backup execution (date/path).

Accompanying elements: a table distinguishing regular inspection (state monthly/quarterly frequency) from ad hoc/special inspection,
plus an **example inspection deliverable form** (host-level normal/abnormal matrix + the Korean field "종합의견").
A field for findings and recommendations demonstrates that inspection is substantive.

## 3. Test approach matrix (type A — support chapter)

Four columns: `Category (area) | Major item | Subitem | Description`. Conventional areas:

- Network availability (NIC redundancy failover), service availability (verify service after node failure),
  configuration changes (deployment automation/settings updates), functions (each core capability),
  disaster recovery (component recovery), expansion (online node/storage expansion), benchmarking (name tools).
- State performance/load metrics: Throughput, transactions per second (TPS), requests per second,
  change in system-resource utilization. Procedure: scenario → load generation/monitoring → bottleneck analysis → improvement.
- Present **cutover/go-live as 4 stages and 8 detailed steps**:
  acceptance testing (prepare → execute → incorporate results) → pilot operation (operate → check readiness) →
  go-live preparation (pre-run → production application) → stabilization (post-go-live operation).
  Attach checklist items to every detailed step.

## 4. Migration methodology (cutover/migration projects)

Five stages: **Environment analysis** (AS-IS, TO-BE) → **Diagnosis/planning** (impact, risks, staged plan) →
**Conversion/migration** (name tools) → **Verification/tuning** (integrated functional/performance tests, performance report) →
**Training/knowledge transfer** (operations/development guides, issue casebook, results report).

Analyze four perspectives: SW (stack/compiler dependencies), HW (architecture/peripheral compatibility),
Service (business relationships/stability during migration), Data (integrity/binary compatibility).
Show the post-migration **stabilization period (freezing)** in the schedule.
Tabulate how incompatible items will be handled (modify/replace/exclude).

### Phased migration (risk reduction) page — when migration is a high-weight criterion

- **Wave design**: pilot (few, low-risk) → general → critical (high-risk). Tabulate four allocation criteria:
  business criticality, integration complexity, data scale, permitted downtime.
  Fill Wave quantities from current-state analysis; no arbitrary allocation, and label assumptions.
- **Go/No-Go gates**: a decision gate between Waves. State criteria (functional-test pass rate,
  performance versus baseline, open defect severity, operational readiness) and decision authority.
- **Parallel operation/rollback**: mandatory parallel period, rollback time limit, rollback criteria, restoration procedure.
  Absence of rollback planning causes risk-management deductions.
- **Performance baseline**: measure before migration → compare afterward under identical conditions.
  Tabulate metrics and conditions.
- **Platform conversion (U2L etc.) checks**: CPU architecture change (endianness/binary compatibility),
  compiler dependencies, charset conversion, data integrity (exhaustive record-count/total/checksum comparison).

### Schedule estimation

Standard-duration data comes only from organizational delivery records; this skill supplies no arbitrary benchmarks.
Build schedules from ①organizational track records with sources or ②working backward from the RFP period.
Without evidence, including unattended execution, **label the entire schedule as assumed**.
Conventional phases: initiation/analysis-design → migration Waves (N) → stabilization/closure.
Show overlapping Waves and stabilization in the Gantt chart.

## 5. Knowledge transfer and training (all types)

- Conventionally use **5 parallel channels**: ①specialist courses ②stage review meetings ③joint build participation
  ④joint operations during stabilization ⑤on-site training during maintenance.
  Procedure: plan (scope, attendees, schedule) → execute (analysis/design → build/test → operations) →
  evaluate (target-level attainment; repeat if unmet).
- Course table: `Course | Content | Audience | Location | Days | Paid/free | Number of sessions`.
  Separate proposer-provided free training (practical operations/issue sharing) from manufacturer formal courses
  (paid; name/days). Specify headcount and conditions for free provision.
  Verify actual manufacturer course names/days/costs **on the official online training catalog**;
  follow research rules and do not name courses from memory.
- For organization-wide rollout, use the **Agent model**: select departmental key staff →
  intensive training/pilot → Agent-led departmental rollout training + a single communication channel.

## 6. Differentiation/additional-offer cards (winning factors — additional proposals)

Actual non-price differentiation categories (select 2~4 relevant to the project):

Free preliminary consulting (half-day~1 day, problem-definition session), advanced technical workshops
(turn identified problems into execution plans), scenario-based demo/validation environments
(requirement-based pilots rather than feature demonstrations), regular technical seminars
(trends/adoption cases), executive briefings, leading-case benchmarking support,
operations manuals and incident-recovery manuals.

Each card must identify format (duration/headcount/conditions) and provider, turning a slogan into a commitment.

## 7. Outsourcing/managed operations (type B variant)

- **Service boundaries**: a 2-column included/excluded table; do not hide exclusions (prevents Exit disputes).
- **RACI**: `Task | Buyer | Contractor | Third party (vendor etc.)`, with R (execute)/A (approve)/C (consult)/I (inform).
  No vague shared assignment: exactly one A.
- **Transition/takeover**: incumbent→contractor stages: documents/assets → shadowing →
  independent operations → stabilization. State duration, completion criteria, incumbent-cooperation assumptions.
- **Exit**: proactively specify handover duties at contract end: deliverable/data/account return list,
  successor handover period/scope, intellectual-property ownership. Missing Exit planning causes deductions;
  credible Exit terms can themselves differentiate trustworthiness.

### Security-product maintenance asset register (multi-product MSS/integrated management)

For multiple security solutions in one maintenance/management contract, use an asset register rather than a product list:
`Product | Quantity (SET) | Location | License period | Inspection frequency | Manufacturer | Commitment secured?`.
Track license expiry, manufacturer commitments (support/supply letters), and inspection frequency together
to prevent missed renewals and insufficient pre-contract commitments.
Fill actual product names/quantities/periods from the RFP/current assets; leave unknowns `[NEEDS INPUT]`.

**Two-track SLA (continuous + regular)**: when both Korean requirements "24x365 상시 지원" and
"월 N회 방문 정기점검" apply, separate them rather than treating them as contradictory:
continuous (remote/emergency, response/recovery targets) + regular (site visit date, deliverable, reporting deadline).
Failure to distinguish channels, targets, and frequencies of both tracks causes deductions.

### Resident staffing subpattern

- **Individual capability/evidence**: separate company records from personal direct delivery records;
  connect experience, qualifications, similar work to evidence IDs. Actual names/contact details only in approved submission copies.
- **Work boundaries**: hours/location, resident/visiting scope, night/holiday response, instruction/approval authority.
- **Continuity**: notice for leave/sickness/departure, equivalent-or-better replacement criteria, buyer approval,
  account revocation, handover completion. Do not promise backup staff before actually securing and approving them.
- **Single-person dependency**: identify task/account/knowledge single points of failure; propose documentation,
  cross-review, replacement. Without approved evidence, target times/headcounts remain `[NEEDS INPUT]`.
- **Compliance**: authorized people review privacy, confidentiality, least privilege, conflicts of interest,
  applicable labor/dispatch conditions. AI does not determine legal conformance.

## 8. Two-track quality assurance (type A — management chapter)

Six-column table: `Type | Stage | Review items | Frequency | Inspection criteria | Participants`.

- **Deliverable review**: team review (as needed, accuracy/standards) → business-requirements review
  (on completion) → manager approval (stage end).
- **Quality assurance evaluation**: audit-style gate at each stage end to decide progression and project-requirement fulfillment.
  Explicit buyer PM participation demonstrates transparency.

### Security completion evidence for financial-sector builds

Map financial RFP specialist evaluation, infrastructure/source vulnerabilities, secure coding, SBOM,
and cloud-safety requirements into:
`Control | RFP/regulatory location | Actor | Timing | Tool/organization | Completion evidence |
Remediation complete | Residual-risk approval`.
Completion includes remediation, retesting, approval of discovered defects, rather than merely running an assessment.
Unapproved organizations/tools/schedules must remain blocking inputs, never promises.
