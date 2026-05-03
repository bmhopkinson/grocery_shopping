import { useState, useRef } from 'react'
import {
  Box, Button, Typography, Alert, CircularProgress, Divider, Paper,
} from '@mui/material'
import FileDownloadIcon from '@mui/icons-material/FileDownload'
import FileUploadIcon from '@mui/icons-material/FileUpload'

export default function Management() {
  const [importStatus, setImportStatus] = useState(null) // { type: 'success'|'error', message }
  const [importing, setImporting] = useState(false)
  const fileInputRef = useRef(null)

  function handleExport() {
    window.location.href = '/api/export'
  }

  async function handleImportFile(e) {
    const file = e.target.files[0]
    if (!file) return
    e.target.value = ''

    setImporting(true)
    setImportStatus(null)

    const form = new FormData()
    form.append('file', file)

    try {
      const res = await fetch('/api/import', { method: 'POST', body: form })
      const data = await res.json()
      if (!res.ok) {
        setImportStatus({ type: 'error', message: data.detail ?? 'Import failed.' })
      } else {
        const { imported } = data
        const summary = Object.entries(imported)
          .map(([k, v]) => `${v} ${k.replace(/_/g, ' ')}`)
          .join(', ')
        setImportStatus({ type: 'success', message: `Imported: ${summary}.` })
      }
    } catch (err) {
      setImportStatus({ type: 'error', message: `Network error: ${err.message}` })
    } finally {
      setImporting(false)
    }
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <Paper variant="outlined" sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>Export Data</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Download all your data — recipes, shopping lists, usuals, and weekly meals — as a JSON file.
        </Typography>
        <Button
          variant="contained"
          startIcon={<FileDownloadIcon />}
          onClick={handleExport}
        >
          Download Export
        </Button>
      </Paper>

      <Divider />

      <Paper variant="outlined" sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>Import Data</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Restore from a previously exported JSON file. This will <strong>replace all existing data</strong>.
        </Typography>
        <Button
          variant="outlined"
          startIcon={importing ? <CircularProgress size={18} /> : <FileUploadIcon />}
          onClick={() => fileInputRef.current?.click()}
          disabled={importing}
        >
          {importing ? 'Importing…' : 'Choose File to Import'}
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          accept="application/json,.json"
          style={{ display: 'none' }}
          onChange={handleImportFile}
        />
        {importStatus && (
          <Alert severity={importStatus.type} sx={{ mt: 2 }} onClose={() => setImportStatus(null)}>
            {importStatus.message}
          </Alert>
        )}
      </Paper>
    </Box>
  )
}
