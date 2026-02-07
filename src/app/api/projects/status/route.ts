import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

const DATA_FILE = path.join(process.cwd(), 'data', 'project-status.json');

export async function GET() {
  try {
    if (!fs.existsSync(DATA_FILE)) return NextResponse.json({ projects: {}, summary: { total: 0 } });
    const data = JSON.parse(fs.readFileSync(DATA_FILE, 'utf-8'));
    const projects = Object.entries(data.projects || {});
    const summary = {
      total: projects.length,
      healthy: projects.filter(([_, p]: [string, any]) => p.status === 'healthy').length,
      degraded: projects.filter(([_, p]: [string, any]) => p.status === 'degraded').length,
      critical: projects.filter(([_, p]: [string, any]) => p.status === 'critical').length
    };
    return NextResponse.json({ ...data, summary });
  } catch { return NextResponse.json({ projects: {} }); }
}
