'use client'

import { useEffect, useState } from 'react'
import { io } from 'socket.io-client'
import Link from 'next/link'
import { use } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'
import { Line } from 'react-chartjs-2'
import { jsPDF } from 'jspdf'

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

// Constants for score calculation
const BULLSEYE_RADIUS = 0.2      // Perfect shot radius in mm
const TEN_RING_RADIUS = 2.482    // 10.0 score radius in mm
const MAX_SCORE = 10.9           // Maximum possible score
const SCORE_DECREASE = 0.394     // Score decrease constant (0.9 / 2.282)

// Score calculation based on calibrated piecewise linear formula
const calculateScore = (x: number, y: number) => {
  // Convert coordinates from meters to millimeters
  const xMM = x * 1000
  const yMM = y * 1000
  
  // Calculate radial distance from center in mm
  const radius = Math.sqrt(xMM * xMM + yMM * yMM)
  
  // Piecewise scoring function
  let score
  if (radius <= BULLSEYE_RADIUS) {
    // Perfect shot - bullseye
    score = MAX_SCORE
  } else if (radius <= TEN_RING_RADIUS) {
    // Linear decrease between bullseye and 10.0 ring
    score = MAX_SCORE - SCORE_DECREASE * (radius - BULLSEYE_RADIUS)
  } else {
    // Below 10.0 score
    // TODO: Implement scoring for outer rings if needed
    score = 10.0
  }
  
  // Round to one decimal place
  return Math.round(score * 10) / 10
}

export default function RacePage({ params }: { params: Promise<{ shooter: string; raceId: string }> }) {
  const { shooter, raceId } = use(params)
  const [shots, setShots] = useState([])
  const [isConnected, setIsConnected] = useState(false)
  const [totalScore, setTotalScore] = useState(0)

  useEffect(() => {
    // Initial data load
    fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/shots?user_id=${shooter}&race_id=${raceId}`)
      .then(res => res.json())
      .then(data => setShots(data.shots || []))

    // WebSocket setup
    const socket = io(process.env.NEXT_PUBLIC_API_BASE_URL, {
      path: '/api/socket'
    })

    socket.on('connect', () => setIsConnected(true))
    socket.on('disconnect', () => setIsConnected(false))

    socket.emit('subscribeToRace', { shooter, raceId })

    socket.on('newShot', (shot) => {
      setShots(prev => {
        const newShots = [...prev, shot]
        const newTotalScore = newShots.reduce((sum, s) => 
          sum + calculateScore(s.shot_data.x, s.shot_data.y), 0
        )
        setTotalScore(newTotalScore)
        return newShots
      })
    })

    return () => {
      socket.off('connect')
      socket.off('disconnect')
      socket.off('newShot')
      socket.disconnect()
    }
  }, [shooter, raceId])

  const exportToPDF = () => {
    const doc = new jsPDF()
    doc.text(`Střelec: ${shooter}`, 20, 20)
    doc.text(`Závod: ${raceId}`, 20, 30)
    doc.text(`Celkové skóre: ${totalScore}`, 20, 40)

    shots.forEach((shot, index) => {
      const y = 50 + (index * 10)
      const score = calculateScore(shot.shot_data.x, shot.shot_data.y)
      doc.text(
        `Rána ${index + 1}: X=${shot.shot_data.x.toFixed(3)}, Y=${shot.shot_data.y.toFixed(3)}, Skóre=${score}`,
        20,
        y
      )
    })

    doc.save(`${shooter}-${raceId}.pdf`)
  }

  const chartData = {
    labels: shots.map((_, i) => `Rána ${i + 1}`),
    datasets: [{
      label: 'Skóre',
      data: shots.map(shot => calculateScore(shot.shot_data.x, shot.shot_data.y)),
      borderColor: 'rgb(75, 192, 192)',
      backgroundColor: 'rgba(75, 192, 192, 0.5)',
      tension: 0.1
    }]
  }

  const chartOptions = {
    responsive: true,
    scales: {
      y: {
        beginAtZero: true,
        max: MAX_SCORE,
        ticks: {
          stepSize: 0.1  // Show each decimal score
        },
        title: {
          display: true,
          text: 'Skóre'
        }
      },
      x: {
        title: {
          display: true,
          text: 'Pořadí rány'
        }
      }
    }
  }

  return (
    <main className="min-h-screen p-8 bg-gray-100">
      <div className="mb-8">
        <Link 
          href={`/${shooter}`}
          className="text-blue-600 hover:text-blue-800 hover:underline mb-4 inline-block"
        >
          ← Zpět na závody
        </Link>
        <h1 className="text-3xl font-bold mb-4 text-gray-800">
          {shooter} - Závod {raceId}
        </h1>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div 
              className={`w-3 h-3 rounded-full ${
                isConnected ? 'bg-green-500' : 'bg-red-500'
              }`}
            />
            <span className="text-sm text-gray-600">
              {isConnected ? 'Live spojení aktivní' : 'Odpojeno'}
            </span>
          </div>
          <div className="flex gap-4">
            <span className="text-xl font-bold">
              Celkové skóre: {totalScore}
            </span>
            <button
              onClick={exportToPDF}
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              Export PDF
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-8">
        <div className="space-y-8">
          {/* Target visualization */}
          <div className="bg-white p-6 rounded-lg shadow-lg">
            <h2 className="text-xl font-semibold mb-4 text-gray-800">Terč</h2>
            <div className="w-[400px] h-[400px] mx-auto">
              <div className="aspect-square w-full border-4 border-gray-300 rounded-full relative bg-white">
                {[...Array(10)].map((_, i) => (
                  <div
                    key={i}
                    className="absolute border border-gray-300 rounded-full"
                    style={{
                      left: `${50 - (i + 1) * 5}%`,
                      top: `${50 - (i + 1) * 5}%`,
                      width: `${(i + 1) * 10}%`,
                      height: `${(i + 1) * 10}%`,
                    }}
                  >
                    <span className="absolute -right-5 top-1/2 -translate-y-1/2 text-xs">
                      {10 - i}
                    </span>
                  </div>
                ))}
                {shots.map((shot, index) => (
                  <div
                    key={index}
                    className="absolute transform -translate-x-1/2 -translate-y-1/2 transition-all duration-300"
                    style={{
                      left: `${50 + (shot.shot_data.x * 1000)}%`,
                      top: `${50 + (shot.shot_data.y * 1000)}%`,
                    }}
                  >
                    <div className="w-2 h-2 bg-red-500 rounded-full" />
                    <div className="absolute top-3 left-3 text-xs font-bold">
                      {index + 1}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Score chart */}
          <div className="bg-white p-6 rounded-lg shadow-lg">
            <h2 className="text-xl font-semibold mb-4 text-gray-800">Graf skóre</h2>
            <Line data={chartData} options={chartOptions} />
          </div>
        </div>

        {/* Shot list */}
        <div className="bg-white p-6 rounded-lg shadow-lg">
          <h2 className="text-xl font-semibold mb-4 text-gray-800">Seznam ran</h2>
          <div className="space-y-2 max-h-[600px] overflow-y-auto">
            {shots.map((shot, index) => (
              <div
                key={index}
                className="p-4 bg-gray-50 rounded shadow hover:bg-gray-100 transition-colors"
              >
                <div className="flex justify-between items-center">
                  <span className="font-bold">Rána #{index + 1}</span>
                  <span className="text-lg font-bold text-blue-600">
                    Skóre: {calculateScore(shot.shot_data.x, shot.shot_data.y)}
                  </span>
                </div>
                <p className="text-gray-600">Čas: {shot.shot_data.time}</p>
                <p className="text-gray-600">X: {shot.shot_data.x.toFixed(3)}</p>
                <p className="text-gray-600">Y: {shot.shot_data.y.toFixed(3)}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </main>
  )
}
