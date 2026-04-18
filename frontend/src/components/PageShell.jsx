import { Box, Button, Container, Paper } from '@mui/material'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'

export default function PageShell({ onBack, header, children }) {
  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Paper elevation={3} sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
          <Button startIcon={<ArrowBackIcon />} onClick={onBack} size="small" sx={{ mr: 2 }}>
            Home
          </Button>
          <Box sx={{ flex: 1 }}>{header}</Box>
        </Box>
        {children}
      </Paper>
    </Container>
  )
}
