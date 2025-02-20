import { NextResponse } from 'next/server'
import path from 'path'
import fs from 'fs/promises'
import { emitNewShot } from '../socket/route'

const DATA_DIR = path.join(process.cwd(), 'data', 'shots')

async function ensureDir(dirPath: string) {
  try {
    await fs.access(dirPath)
  } catch {
    await fs.mkdir(dirPath, { recursive: true })
  }
}

export async function POST(request: Request) {
  try {
    const data = await request.json()
    const { user_id, race_id, shot_data } = data

    // Basic validation
    if (!user_id || !race_id || !shot_data) {
      return NextResponse.json(
        { error: 'Missing required fields' },
        { status: 400 }
      )
    }

    // Create user and race directories
    const userDir = path.join(DATA_DIR, user_id)
    const raceDir = path.join(userDir, race_id)
    await ensureDir(raceDir)

    // Save shot data
    const timestamp = new Date().toISOString()
    const shotData = {
      user_id,
      race_id,
      timestamp,
      shot_data
    }
    const filename = `${timestamp}.json`
    const filepath = path.join(raceDir, filename)

    await fs.writeFile(filepath, JSON.stringify(shotData, null, 2))

    // Emit new shot event
    emitNewShot(user_id, race_id, shotData)

    return NextResponse.json({ success: true, timestamp })

  } catch (error) {
    console.error('Error saving shot:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const user_id = searchParams.get('user_id')
  const race_id = searchParams.get('race_id')

  try {
    // Return list of all shooters
    if (!user_id) {
      const shooters = await fs.readdir(DATA_DIR)
      return NextResponse.json({ shooters })
    }

    const userDir = path.join(DATA_DIR, user_id)

    // Return list of user's races
    if (!race_id) {
      try {
        const races = await fs.readdir(userDir)
        return NextResponse.json({ races })
      } catch {
        return NextResponse.json({ races: [] })
      }
    }

    // Return shots for specific race
    const raceDir = path.join(userDir, race_id)
    try {
      const files = await fs.readdir(raceDir)
      const shots = await Promise.all(
        files.map(async (file) => {
          const content = await fs.readFile(
            path.join(raceDir, file),
            'utf-8'
          )
          return JSON.parse(content)
        })
      )
      return NextResponse.json({ shots })
    } catch {
      return NextResponse.json({ shots: [] })
    }

  } catch (error) {
    console.error('API Error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
