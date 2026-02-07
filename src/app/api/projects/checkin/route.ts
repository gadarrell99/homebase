import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

const DATA_FILE = path.join(process.cwd(), 'data', 'project-status.json');

function ensureDataDir() {
  const dataDir = path.dirname(DATA_FILE);
  if (!fs.existsSync(dataDir)) fs.mkdirSync(dataDir, { recursive: true });
  if (!fs.existsSync(DATA_FILE)) fs.writeFileSync(DATA_FILE, JSON.stringify({ projects: {} }, null, 2));
}

export async function POST(request: NextRequest) {
  try {
    ensureDataDir();
    const body = await request.json();
    const { project, version, status, milestone, todos_open, todos_done, timestamp } = body;
    if (!project) return NextResponse.json({ error: 'project required' }, { status: 400 });
    const data = JSON.parse(fs.readFileSync(DATA_FILE, 'utf-8'));
    data.projects[project] = {
      version: version || 'unknown', status: status || 'healthy', milestone: milestone || '',
      todos_open: todos_open || 0, todos_done: todos_done || 0,
      last_checkin: timestamp || new Date().toISOString(), updated_at: new Date().toISOString()
    };
    fs.writeFileSync(DATA_FILE, JSON.stringify(data, null, 2));
    return NextResponse.json({ success: true, project });
  } catch (error) {
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}

export async function GET() {
  try {
    ensureDataDir();
    return NextResponse.json(JSON.parse(fs.readFileSync(DATA_FILE, 'utf-8')));
  } catch { return NextResponse.json({ projects: {} }); }
}
