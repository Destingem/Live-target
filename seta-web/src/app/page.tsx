import Link from 'next/link'

async function getShooters() {
  // Add cache: 'no-store' and next: { revalidate: 0 } for real-time data
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/shots`, {
    cache: 'no-store',
    next: { revalidate: 0 }
  })
  if (!res.ok) return []
  const data = await res.json()
  return data.shooters || []
}

export default async function Home() {
  const shooters = await getShooters()

  return (
    <main className="min-h-screen p-8">
      <h1 className="text-3xl font-bold mb-8">SETA Live Results</h1>
      
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {shooters.map((shooter) => (
          <Link 
            href={`/${shooter}`}
            key={shooter}
            className="p-6 bg-white rounded-lg shadow hover:shadow-lg transition-shadow"
          >
            <h2 className="text-xl font-semibold mb-2">{shooter}</h2>
            <p className="text-gray-600">Zobrazit závody →</p>
          </Link>
        ))}
      </div>
    </main>
  )
}
