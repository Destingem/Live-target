import Link from 'next/link'

async function getRaces(shooter: string) {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/shots?user_id=${shooter}`, {
    cache: 'no-store',
    next: { revalidate: 0 }
  })
  if (!res.ok) return []
  const data = await res.json()
  return data.races || []
}

export default async function ShooterPage({
  params: { shooter }
}: {
  params: { shooter: string }
}) {
  const races = await getRaces(shooter)

  return (
    <main className="min-h-screen p-8">
      <div className="mb-8">
        <Link 
          href="/"
          className="text-blue-500 hover:underline mb-4 inline-block"
        >
          ← Zpět na přehled
        </Link>
        <h1 className="text-3xl font-bold">Závody střelce {shooter}</h1>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {races.map((race) => (
          <Link
            href={`/${shooter}/${race}`}
            key={race}
            className="p-6 bg-white rounded-lg shadow hover:shadow-lg transition-shadow"
          >
            <h2 className="text-xl font-semibold mb-2">{race}</h2>
            <p className="text-gray-600">Zobrazit výsledky →</p>
          </Link>
        ))}
      </div>
    </main>
  )
}
