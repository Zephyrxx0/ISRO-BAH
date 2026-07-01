import { NextRequest } from 'next/server';
import { GoogleGenerativeAI } from '@google/generative-ai';

// Initialize Gemini API
const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY || '');

export async function POST(req: NextRequest) {
  try {
    const { ticId, candidateName, disposition, sde, fpp } = await req.json();

    if (!ticId) {
      return new Response(JSON.stringify({ error: 'Missing ticId' }), { status: 400 });
    }

    if (!process.env.GEMINI_API_KEY) {
      return new Response(JSON.stringify({ error: 'GEMINI_API_KEY is not configured.' }), { status: 500 });
    }

    // Step 1: Fetch SIMBAD Data using ADQL via TAP endpoint
    // We search the 'ident' table to find the OID for the TIC ID, then join with 'basic'
    const query = `SELECT basic.MAIN_ID, basic.RA, basic.DEC, basic.SP_TYPE 
                   FROM basic 
                   JOIN ident ON ident.oidref = basic.oid 
                   WHERE ident.id = '${ticId}'`;
    
    let simbadData = '';
    try {
      const tapResponse = await fetch('http://simbad.u-strasbg.fr/simbad/sim-tap/sync', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          request: 'doQuery',
          lang: 'adql',
          format: 'json',
          query: query
        })
      });

      if (tapResponse.ok) {
        const tapJson = await tapResponse.json();
        if (tapJson.data && tapJson.data.length > 0) {
          const row = tapJson.data[0];
          simbadData = `Main ID: ${row[0]}, RA: ${row[1]}, DEC: ${row[2]}, Spectral Type: ${row[3] || 'Unknown'}`;
        } else {
          simbadData = `No direct match found in SIMBAD for ${ticId}.`;
        }
      } else {
        simbadData = `Failed to connect to SIMBAD.`;
      }
    } catch (e) {
      simbadData = `SIMBAD query failed: ${e}`;
    }

    // Step 2: Formulate Prompt
    const prompt = `
You are an expert astrophysicist analyzing exoplanet candidate data.
We have a target: ${candidateName} (TIC ID: ${ticId}).

Here are the pipeline metrics:
- Pipeline Disposition: ${disposition}
- SDE (Signal Detection Efficiency): ${sde}
- TRICERATOPS False Positive Probability (FPP): ${fpp}

Here is the data retrieved from the SIMBAD Astronomical Database:
${simbadData}

Instructions:
Write a professional, 2-paragraph research synthesis evaluating this target's context and viability as an exoplanet. 
In the first paragraph, summarize the astrophysical context (spectral type, location) based only on the SIMBAD data.
In the second paragraph, evaluate the pipeline metrics (SDE, FPP, Disposition) and provide a recommendation on whether this is a strong planet candidate or likely a false positive/eclipsing binary.
CRITICAL GUARDRAIL: Do NOT hallucinate data. Do NOT mention any papers or citations unless you absolutely know them to be true. Stick only to the data provided above.
`;

    // Step 3: Stream from Gemini
    const model = genAI.getGenerativeModel({ model: 'gemini-1.5-pro' });
    const streamingResp = await model.generateContentStream(prompt);

    const stream = new ReadableStream({
      async start(controller) {
        try {
          for await (const chunk of streamingResp.stream) {
            const chunkText = chunk.text();
            controller.enqueue(new TextEncoder().encode(chunkText));
          }
          controller.close();
        } catch (e) {
          controller.error(e);
        }
      },
    });

    return new Response(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });

  } catch (error: any) {
    console.error('AI Synthesis Error:', error);
    return new Response(JSON.stringify({ error: error.message }), { status: 500 });
  }
}
