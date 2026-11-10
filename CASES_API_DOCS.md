# Parent & Student Cases API Documentation

Full API reference for **Parent Cases**, **Student Cases (Above 8)**, and **Student Cases (Below 8)** from the Queunity User Portal.

---

## Common

**Auth:** `Authorization: Bearer <token>` on every endpoint.

**Envelope:**

```json
{ "success": true, "message": "...", "data": {}, "errors": null }
```

**Pagination** (list endpoints): `skip` (≥0), `limit` (1–100), `search` (optional).

**Paginated `data`:**

```json
{ "items": [], "total": 0, "skip": 0, "limit": 0 }
```

**Staged flow (Parent + Student Above 8):**

| Stage | What |
|------|------|
| 1 | Incident basics |
| 2 | Suspects |
| 3 | Witnesses |
| 4 | Evidence |
| 5 | Charity + police |
| 6 | Resolution → submit (`draft: false`, `status: PENDING`) |

Create starts as `draft: true`, `currentStage: 1`. Stage 6 requires stage 5 done.

---

# 1. Parent Cases

Base: `/parent/cases`  
Lookups: `/parent/...`  
Role: **parent** only.

### Lookups

| Method | Path | Notes |
|--------|------|--------|
| GET | `/parent/schools` | paginated |
| GET | `/parent/grades?schoolId=` | `schoolId` required |
| GET | `/parent/offenses` | paginated |
| GET | `/parent/offense-sub-categories?offenseId=` | optional filter |
| GET | `/parent/charities` | paginated |

---

### Cases

#### `POST /parent/cases` → 201

**Body (JSON) — Stage 1**

| Field | Type | Required |
|-------|------|----------|
| `caseName` | string | yes |
| `schoolId` | string \| null | if unset / `"others"` → need `otherSchoolName` |
| `otherSchoolName` | string \| null | when school is others/blank |
| `victimId` | string | yes (one of your children) |
| `offenseId` | string | yes |
| `offenseSubCategoryId` | string | yes |
| `incidentDate` | `YYYY-MM-DD` | yes |
| `incidentTime` | `HH:MM` (24h) | yes |
| `locationType` | `OUTSIDE_SCHOOL` \| `WITHIN_SCHOOL` | yes |
| `areaType` | see enums | optional |
| `areaDescription` | string | required if `areaType=OTHER` |
| `gradeId` | string | rejected if `areaType=OTHER` |
| `anonymityLevel` | enum | yes |
| `privacyLevel` | `LEVEL_1` \| `LEVEL_2` | yes |

#### `GET /parent/cases`

Query: pagination + `status` (`PENDING`\|`RESOLVED`), `draft`, `schoolId`, `charityId`, `offenseId`, `offenseSubCategoryId`, `victimId`.

#### `GET /parent/cases/{case_id}`

Full case + `victim`, `suspects`, `witnesses`, `evidence`.

#### `PATCH /parent/cases/{case_id}/stage1`

Same body as create.

#### `PATCH /parent/cases/{case_id}/stage5` — `multipart/form-data`

| Field | Notes |
|-------|--------|
| `charityInvolvement` | required |
| `policeInvolvement` | required |
| `charityId` / `charityNameFallback` | exactly one if `ALREADY_INFORMED` |
| `charityTypeRequested` | required if `INFORM_NOW` |
| `charityInvolvementReason` | optional for `INFORM_NOW` |
| `policeReportNumber` | required if `ALREADY_REPORTED` |
| `policeOfficerName`, `policeStationDepartment`, `policeReportDate` (`YYYY-MM-DD`), `policeReportImageUrl` | only with `ALREADY_REPORTED` |
| `policeReportImage` | file; only when `ALREADY_REPORTED` |

#### `PATCH /parent/cases/{case_id}/stage6`

```json
{ "resolutionDesired": "ADMIN_DISCRETION" }
```

Submits the case.

#### `DELETE /parent/cases/{case_id}`

---

### Suspects — `/parent/cases/{case_id}/suspects`

All create/update: **`multipart/form-data`**

| Part | Description |
|------|-------------|
| `payload` | JSON string of suspect fields |
| `studentImage` | optional file |
| `physicalFiles` | optional files → `physicalDetails.files` |
| `vehicleFiles` | optional files → `vehicleDetails.files` |
| `existingPhysicalFileUrls` | update only: JSON array of URLs to keep |
| `existingVehicleFileUrls` | update only: JSON array of URLs to keep |

| Method | Path |
|--------|------|
| POST | `` |
| GET | `` |
| GET | `/{suspect_id}` |
| PATCH | `/{suspect_id}` |
| DELETE | `/{suspect_id}` |

**`payload` shape (`isKnown`):**

- **`isKnown: false`** — unknown person: may send `physicalDetails`, `vehicleDetails`, `behaviorObserved`. Do **not** send known-person fields. Do **not** put `files` inside details JSON (upload via form files).

- **`isKnown: true`** + `relationship`:
  - `SCHOOLMATE` → required: `grade`, `studentName`; optional: `studentImageUrl`, `studentDetails`
  - `EXTERNAL_STUDENT` → required: `extSchoolName`, `extSchoolCity`, `extSchoolState`, `studentName`; optional grade/gender/image/details/`howIdentified`
  - `OTHERS` → required: `personName`, `personType`; if `wasOnSchoolGrounds: true` → `whereOnCampusSeen` required

**Physical details (input):** `height`, `build`, `skinTone`, `clothingType`, `hair`, `eyes`, `mouth`, `shoulder`, `handsAndArms`, `torso`, `legs`, `feet`, `accessories`, `additionalInfo`

**Vehicle details (input):** `vehicleType`, `color`, `brand`, `model`, `markings`, `damage`, `registrationNumber`, `additionalInfo`, `directionOfTravel`, `lastSeenLocation`

---

### Witnesses — `/parent/cases/{case_id}/witnesses`

Same multipart pattern as suspects (`payload`, `physicalFiles`, `vehicleFiles`, keep-URL fields on update). No `studentImage`.

| Method | Path |
|--------|------|
| POST / GET | `` |
| GET / PATCH / DELETE | `/{witness_id}` |

**`isKnown: false`:** physical/vehicle/behavior only.

**`isKnown: true`:**

- `SCHOOLMATE` → required: `grade`, `studentName`, `witnessCoverage`, `witnessReliability`, `relationshipToVictim`; optional `witnessStatement`
- `EXTERNAL_STUDENT` → required: `extSchoolName`, `extSchoolCity`, `extSchoolState`
- `OTHERS` → required: `personName`, `personType`, `wasPresent`

---

### Evidence — `/parent/cases/{case_id}/evidence`

`multipart/form-data`

| Method | Path | Body |
|--------|------|------|
| POST | `` | `description?`, `files?` (at least one of description/files) |
| GET | `` | list |
| GET | `/{evidence_id}` | |
| PATCH | `/{evidence_id}` | `description?`, `existingFileUrls?` (JSON array), `files?` |
| DELETE | `/{evidence_id}` | |

---

### Parent case response (`CaseOut`) highlights

`id`, `caseName`, `schoolId`, `otherSchoolName`, `victimId`, `victim`, `offenseId`, `offenseSubCategoryId`, `incidentDate`, `incidentTime`, `locationType`, `areaType`, `areaDescription`, `gradeId`, `grade`, `anonymityLevel`, `privacyLevel`, charity/police fields, `resolutionDesired`, `draft`, `status`, `currentStage` (1–6), `hasEvidence`, `suspects[]`, `witnesses[]`, `evidence[]`, `createdAt`, `updatedAt`

---

# 2. Student Cases (Above 8)

Base: `/student/cases`  
Lookups: `/student/...`  
Role: **student**, age **> 8**. Victim is the logged-in student (no `victimId` on create).

Endpoints mirror parent with prefix `/student` instead of `/parent`, and nested resources under `/student/cases/{case_id}/...`.

### Differences vs parent

| | Parent | Student Above 8 |
|--|--------|-----------------|
| Stage 1 | requires `victimId` | **no** `victimId` |
| List filter | has `victimId` | no `victimId` filter |
| Lookups | `/parent/...` | `/student/...` |
| Auth | parent token | student token |

### Endpoints (same shapes otherwise)

**Lookups:**  
`GET /student/schools|grades|offenses|offense-sub-categories|charities`

**Cases:**  
`POST/GET /student/cases`  
`GET/DELETE /student/cases/{case_id}`  
`PATCH .../stage1` (JSON)  
`PATCH .../stage5` (multipart)  
`PATCH .../stage6` (JSON `{ resolutionDesired }`)

**Suspects / Witnesses / Evidence:** identical multipart + CRUD under  
`/student/cases/{case_id}/suspects|witnesses|evidence`

---

# 3. Student Cases (Below 8)

Base: `/student/below-8/cases`  
Role: **student**, age **≤ 8**. Simple create (no stages/suspects/witnesses/evidence). Auto-sets `victimId`, `schoolId`, `gradeId` from student; `draft: false`, `status: PENDING`. Emails parent/school on create/update.

| Method | Path | Body |
|--------|------|------|
| POST | `` | JSON create |
| GET | `` | paginated (`search` on name/description) |
| GET | `/{case_id}` | |
| PATCH | `/{case_id}` | partial update (at least one field) |
| DELETE | `/{case_id}` | |

**Create:**

```json
{
  "caseName": "string",
  "caseDescription": "string",
  "whenItHappened": "TODAY | YESTERDAY | FEW_DAYS_AGO",
  "whereItHappened": "CLASSROOM | BATHROOM | PLAYGROUND | OTHERS"
}
```

**Update:** any subset of those fields (all optional, but not empty).

---

# Enums (Parent + Student Above 8)

```
LocationType: OUTSIDE_SCHOOL | WITHIN_SCHOOL
AreaType: CLASSROOM | CAFETERIA | PLAYGROUND | HALLWAY | BATHROOM | BUS_AREA | SPORTS_FIELD | COMPUTER_LAB | LIBRARY | OTHER
AnonymityLevel: COMPLETE_ANONYMOUS | STUDENT_SUBJECT_ONLY | HIDE_FROM_PARENTS | DONT_HIDE_IDENTITY
PrivacyLevel: LEVEL_1 | LEVEL_2
CharityInvolvement: ALREADY_INFORMED | INFORM_NOW | MAYBE_LATER | NO
CharityType: COUNSELLING_SUPPORT | CRISIS_INTERVENTION | FAMILY_SUPPORT | MENTAL_HEALTH | ANTI_BULLYING_PARTNER | COMMUNITY_SUPPORT
PoliceInvolvement: ALREADY_REPORTED | MAYBE_LATER | NO
ResolutionDesired: ADMIN_DISCRETION | DISCIPLINE_PER_CONDUCT_POLICY | CLASS_WIDE_INTERVENTION_NO_ID | DISCIPLINE_AND_RESTORATIVE_CIRCLE
CaseStatus: PENDING | RESOLVED
PersonRelationship: SCHOOLMATE | EXTERNAL_STUDENT | OTHERS
PersonType: PARENT | FAMILY_MEMBER | STAFF | COMMUNITY_MEMBER | CONTRACTOR_VISITOR | ONLINE_PERSON | STRANGER | OTHER
WitnessCoverage: ENTIRE_INCIDENT | PARTIALLY | ONLY_HEARD | NOT_SURE
WitnessReliability: HIGH | MEDIUM | LOW | UNKNOWN
RelationshipToVictim: CLASSMATE | FRIEND | TEAM_MEMBER | SIBLING | NO_RELATIONSHIP | UNKNOWN
WasPresent: YES | PARTIALLY | NO | UNKNOWN
```

**School sentinel:** `schoolId: "others"` (case-insensitive) → requires `otherSchoolName`; stored `schoolId` becomes `null`.

---

### Typical Above-8 wizard order

1. Lookups → `POST .../cases` (stage 1)
2. Suspects CRUD
3. Witnesses CRUD
4. Evidence CRUD
5. `PATCH .../stage5`
6. `PATCH .../stage6` (submit)

Interactive OpenAPI is also on the running app at `/docs` (tags: Parent Cases / Student Cases (Above 8) / Student Cases (Below 8)).
