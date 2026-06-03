import { NextResponse } from "next/server";

import {
  listTemplateCatalog,
  readTemplateFile,
} from "@/lib/circuitTemplateCatalog";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const action = body?.action;

    if (action === "list") {
      const templates = listTemplateCatalog();
      return NextResponse.json({ ok: true, templates });
    }

    if (action === "get") {
      const filename = body?.filename;
      if (!filename || typeof filename !== "string") {
        return NextResponse.json(
          { ok: false, error: "filename is required." },
          { status: 400 },
        );
      }
      const template = readTemplateFile(filename);
      return NextResponse.json({ ok: true, ...template });
    }

    return NextResponse.json(
      { ok: false, error: "Unknown action. Use 'list' or 'get'." },
      { status: 400 },
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    const status = message.includes("not found") ? 404 : 400;
    return NextResponse.json({ ok: false, error: message }, { status });
  }
}

export async function OPTIONS() {
  return NextResponse.json({ ok: true });
}
