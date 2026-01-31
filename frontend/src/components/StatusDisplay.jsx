import { Box, Typography, LinearProgress, Chip, Stack } from '@mui/material'

export default function StatusDisplay({ messages, loading }) {
  if (messages.length === 0 && !loading) return null

  return (
    <Box sx={{ mb: 3 }}>
      {loading && <LinearProgress sx={{ mb: 2 }} />}
      {messages.length > 0 && (
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          {messages.slice(-5).map((msg, idx) => (
            <Chip
              key={idx}
              label={msg}
              size="small"
              variant="outlined"
              color={idx === messages.length - 1 ? 'primary' : 'default'}
            />
          ))}
        </Stack>
      )}
    </Box>
  )
}
