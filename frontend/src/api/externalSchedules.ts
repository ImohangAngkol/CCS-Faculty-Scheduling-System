import {z} from "zod";
import {apiClient, API_BASE} from "../services/apiSession.ts";
import type {CompletionMetadata, ReadinessAssessment} from "./externalReadiness.ts";

const row = z.object({
  supplier: z.string(), subject_code: z.string(), title: z.string(), sections: z.array(z.string()),
  academic_term: z.string(), days: z.array(z.string()), start: z.string(), end: z.string(),
  room: z.string(), instructor: z.string(), source_reference: z.string(), notes: z.string(),
  status: z.enum(["draft", "tentative"]),
}).strict();
export type ExternalRow = z.infer<typeof row>;
const match = z.object({value: z.string(), id: z.string().nullable(), state: z.enum(["resolved", "unresolved", "not_supplied"])}).strict();
const discrepancy = z.object({code: z.string(), severity: z.enum(["error", "review"]), field: z.string(), message: z.string(), related_rows: z.array(z.number().int().positive())}).strict();
export const legacyMetadataSchema = z.object({supplier: z.string().max(120), source_reference: z.string().max(250), academic_term: z.string().max(120), status: z.enum(["draft", "tentative"])}).strict();
export type LegacyMetadata = z.infer<typeof legacyMetadataSchema>;
const legacySchema = z.object({adapter_version: z.literal("d6.1"), metadata_origin: z.literal("administrator_supplied_unverified"), metadata: legacyMetadataSchema,
  rows: z.array(z.object({source_row: z.number().int().positive(), year_level: z.string(), section: z.string(), course_number: z.string(), schedule: z.string(),
    parse_state: z.enum(["parsed", "invalid", "unsupported", "ambiguous"]), discrepancies: z.array(discrepancy)}).strict()).max(200)}).strict();
export const previewSchema = z.object({
  schema_version: z.literal(1), preview_only: z.literal(true), persisted: z.literal(false), activated: z.literal(false),
  source_kind: z.enum(["manual", "csv", "xlsx"]), source_name: z.string().nullable(), source_sha256: z.string().regex(/^[a-f0-9]{64}$/).nullable(),
  parser_version: z.literal("d3.1"), term_verification: z.literal("not_configured"),
  rows: z.array(z.object({source_row: z.number().int().positive(), input: row,
    status: z.enum(["draft", "tentative", "needs_review", "invalid"]), sections: z.array(match), room: match, instructor: match,
    discrepancies: z.array(discrepancy)}).strict()).max(200),
  review_token: z.string().max(1600000).nullable().optional(),
  legacy: legacySchema.nullable().optional(),
}).strict();
export type ExternalPreview = z.infer<typeof previewSchema>;
const reference = z.object({id: z.string(), label: z.string(), alias: z.string().optional()}).strict();
export const metadataSchema = z.object({
  sections: z.array(reference), rooms: z.array(reference), instructors: z.array(reference),
  subjects: z.array(z.object({code: z.string(), title: z.string()}).strict()),
  terms: z.array(z.never()), term_verification: z.literal("not_configured"), fixed_section_entries: z.number().int().nonnegative(),
  limits: z.object({max_bytes: z.literal(1048576), max_rows: z.literal(200), max_columns: z.literal(13), xlsx_sheets: z.literal(1), max_decompressed_bytes: z.literal(8388608)}).strict(),
}).strict();
export type ExternalMetadata = z.infer<typeof metadataSchema>;
const endpoint = API_BASE + "/api/external-schedules";

export function emptyExternalRow(): ExternalRow {
  return {supplier: "", subject_code: "", title: "", sections: [], academic_term: "", days: [], start: "", end: "",
    room: "", instructor: "", source_reference: "", notes: "", status: "draft"};
}
export async function getExternalMetadata(signal?: AbortSignal): Promise<ExternalMetadata> {
  return metadataSchema.parse((await apiClient.get(endpoint + "/metadata", {signal})).data);
}
export async function previewManual(rows: ExternalRow[], signal?: AbortSignal): Promise<ExternalPreview> {
  return previewSchema.parse((await apiClient.post(endpoint + "/preview", {rows}, {signal})).data);
}
export async function previewFile(file: File, signal?: AbortSignal, legacyMetadata?: LegacyMetadata): Promise<ExternalPreview> {
  if (file.size > 1048576 || !/\.(csv|xlsx)$/i.test(file.name))
    throw new Error("Choose a CSV or XLSX file no larger than 1 MiB.");
  if (legacyMetadata && !/\.csv$/i.test(file.name)) throw new Error("Legacy GEC preview requires a UTF-8 CSV file.");
  let payload: File | {content_base64: string; metadata: LegacyMetadata} = file;
  if (legacyMetadata) {
    const bytes = new Uint8Array(await file.arrayBuffer());
    let binary = "";
    for (let i = 0; i < bytes.length; i += 8192) binary += String.fromCharCode(...bytes.subarray(i, i+8192));
    payload = {content_base64: btoa(binary), metadata: legacyMetadataSchema.parse(legacyMetadata)};
  }
  return previewSchema.parse((await apiClient.post(endpoint + "/preview-file", payload, {
    signal, params: {filename: file.name, ...(legacyMetadata ? {import_format: "legacy_gec"} : {})}, headers: {"Content-Type": legacyMetadata ? "application/json" : "application/octet-stream"},
  })).data);
}

const resolution = z.object({
  original: z.string(), id: z.string().nullable(), label: z.string().nullable(),
  state: z.enum(["resolved", "unresolved", "ambiguous", "unsupported", "missing_optional"]),
  method: z.enum(["recognized", "explicit", "none"]), candidate_ids: z.array(z.string()),
}).strict().refine(value => value.state === "resolved"
  ? value.id !== null && value.label !== null && value.method !== "none"
  : value.id === null && value.label === null && value.method === "none");
export const reviewProjectionSchema = z.object({
  schema_version: z.literal(2), preview_only: z.literal(true), persisted: z.literal(false), activated: z.literal(false),
  source_kind: z.enum(["manual", "csv", "xlsx"]), source_name: z.string().nullable(),
  source_sha256: z.string().regex(/^[a-f0-9]{64}$/).nullable(), source_parser_version: z.literal("d3.1"),
  projection_version: z.literal("d4.1"), term_verification: z.literal("not_configured"),
  reference_digest: z.string().regex(/^[a-f0-9]{64}$/),
  rows: z.array(z.object({source_row: z.number().int().positive(), original: row,
    status: z.enum(["draft", "tentative", "needs_review", "invalid"]),
    sections: z.array(resolution), room: resolution, instructor: resolution,
    discrepancies: z.array(discrepancy), calendar_supported: z.boolean()}).strict()).max(200),
  legacy: legacySchema.nullable().optional(),
}).strict();
export type ReviewProjection = z.infer<typeof reviewProjectionSchema>;
export type ReviewMeeting = ReviewProjection["rows"][number];
export type ResourceResolution = ReviewMeeting["room"];
export type RowMapping = {source_row: number; sections?: {reference_index: number; target_id: string}[]; room_id?: string | null; instructor_id?: string | null};

export async function reviewExternal(source: ExternalPreview, mappings: RowMapping[], signal?: AbortSignal): Promise<ReviewProjection> {
  if (!source.review_token) throw new Error("Preview the source again with the current backend before reconciling resources.");
  const response = await apiClient.post(endpoint + "/review", {review_token: source.review_token, mappings}, {signal});
  return verifyReview(source, response.data);
}

function verifyReview(source: ExternalPreview, value: unknown): ReviewProjection {
  const parsed = reviewProjectionSchema.safeParse(value);
  if (!parsed.success) throw new Error("The reconciled preview could not be verified.");
  const data = parsed.data, lines = new Set(data.rows.map(r => r.source_row));
  if (data.source_sha256 !== source.source_sha256 || data.source_kind !== source.source_kind || data.source_name !== source.source_name
      || data.rows.length !== source.rows.length || lines.size !== data.rows.length
      || JSON.stringify(data.legacy ?? null) !== JSON.stringify(source.legacy ?? null)
      || data.rows.some(r => JSON.stringify(r.original) !== JSON.stringify(source.rows.find(original => original.source_row === r.source_row)?.input)))
    throw new Error("The review does not match the original preview provenance. Preview the source again.");
  return data;
}

export const HANDOFF_LABEL = "REVIEW PREVIEW — NOT CONFIRMED OR ACTIVE IN GA";
export const handoffSchema = z.object({
  schema_version: z.literal(3), handoff_version: z.literal("d5.1"), label: z.literal(HANDOFF_LABEL),
  preview_only: z.literal(true), persisted: z.literal(false), activated: z.literal(false), approved: z.literal(false),
  preview_id: z.string().regex(/^d5-[a-f0-9]{64}$/), revalidated_at: z.string().datetime({offset: true}),
  review: reviewProjectionSchema,
  readiness: z.unknown().optional(),
}).strict();
export type ReviewHandoff = Omit<z.infer<typeof handoffSchema>, "readiness"> & {readiness?: ReadinessAssessment};

// Matches the server's sorted ASCII JSON. The ID is a content fingerprint,
// never an authorization token, supplier attestation or approval identifier.
export async function handoffIdentity(value: unknown): Promise<string> {
  function canonical(item: unknown): string {
    if (Array.isArray(item)) return "[" + item.map(canonical).join(",") + "]";
    if (item !== null && typeof item === "object") return "{" + Object.keys(item).sort().map(key => canonical(key) + ":" + canonical((item as Record<string, unknown>)[key])).join(",") + "}";
    return JSON.stringify(item).replace(/[\u0080-\uffff]/g, char => "\\u" + char.charCodeAt(0).toString(16).padStart(4, "0"));
  }
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(canonical(value)));
  return "d5-" + [...new Uint8Array(digest)].map(byte => byte.toString(16).padStart(2, "0")).join("");
}

export async function prepareExternalHandoff(source: ExternalPreview, mappings: RowMapping[], signal?: AbortSignal, readiness?: {metadata: CompletionMetadata; assessment_receipt: string}): Promise<ReviewHandoff> {
  if (!source.review_token) throw new Error("Preview the source again before preparing a review handoff.");
  const response = await apiClient.post(endpoint + "/handoff", {review_token: source.review_token, mappings, ...readiness}, {signal});
  const parsed = handoffSchema.safeParse(response.data);
  if (!parsed.success) throw new Error("The review handoff could not be verified.");
  const data = parsed.data;
  verifyReview(source, data.review);
  if (readiness) {
    const {verifyAssessment} = await import("./externalReadiness.ts");
    data.readiness = await verifyAssessment(data.readiness, source, readiness.metadata);
  } else if (data.readiness !== undefined) throw new Error("Unexpected readiness assessment in an unassessed handoff.");
  if (await handoffIdentity(readiness ? {review:data.review,readiness:data.readiness} : data.review) !== data.preview_id) throw new Error("The handoff identity does not match its complete review content.");
  return data as ReviewHandoff;
}
