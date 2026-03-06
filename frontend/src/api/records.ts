import { api } from "./client";
import type { RecordsImportResultDto } from "./dto";
import { apiPaths } from "./paths";

export async function importRecords(
  patientId: number,
  file: File,
): Promise<RecordsImportResultDto> {
  const formData = new FormData();
  formData.append("patient_id", String(patientId));
  formData.append("file", file);

  const response = await api.post<RecordsImportResultDto>(
    apiPaths.records.import,
    formData,
    {
      headers: { "Content-Type": "multipart/form-data" },
    },
  );
  return response.data;
}
