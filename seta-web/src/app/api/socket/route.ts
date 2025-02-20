import { Server } from 'socket.io'
import { NextApiResponse } from 'next'
import { createServer } from 'http'

const io = new Server({
  path: '/api/socket',
  addTrailingSlash: false,
})

const httpServer = createServer()
io.attach(httpServer)

io.on('connection', (socket) => {
  console.log('Client connected')
  
  socket.on('subscribeToRace', (data) => {
    const { shooter, raceId } = data
    socket.join(`${shooter}-${raceId}`)
  })
  
  socket.on('disconnect', () => {
    console.log('Client disconnected')
  })
})

export function emitNewShot(shooter: string, raceId: string, shot: any) {
  io.to(`${shooter}-${raceId}`).emit('newShot', shot)
}

export { io }
