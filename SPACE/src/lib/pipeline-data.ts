import fs from 'fs';
import path from 'path';
import { PipelinePayload, CandidateEntry } from '../../outputs/integration-schema';
import { generateMockPayload } from '../utils/mock-generator';

export function getPipelineData(): PipelinePayload {
  let pipelineData: PipelinePayload | null = null;

  try {
    const filePath = path.join(process.cwd(), '../outputs/pipeline-payload.json');
    if (fs.existsSync(filePath)) {
      const fileContents = fs.readFileSync(filePath, 'utf8');
      pipelineData = JSON.parse(fileContents);
    }
  } catch (error) {
    console.error("Error reading pipeline payload:", error);
  }

  const mockData = generateMockPayload(18);

  if (!pipelineData) {
    return mockData;
  }

  // Merge candidates (real data takes precedence if there are duplicates)
  return {
    ...pipelineData,
    candidates: {
      ...mockData.candidates,
      ...pipelineData.candidates
    }
  };
}

export function getAllCandidates(): CandidateEntry[] {
  const data = getPipelineData();
  return Object.values(data.candidates);
}

export function getCandidateById(ticId: string): CandidateEntry | undefined {
  const data = getPipelineData();
  const normalizedId = ticId.replace(/\s+/g, '');
  return Object.values(data.candidates).find(
    c => c.signal.ticId.replace(/\s+/g, '') === normalizedId
  );
}
