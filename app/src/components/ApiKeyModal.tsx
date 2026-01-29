import { useState } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Box,
  Typography,
  Alert,
} from "@mui/material";

interface ApiKeyModalProps {
  open: boolean;
  onSubmit: (apiKey: string) => void;
}

export default function ApiKeyModal({ open, onSubmit }: ApiKeyModalProps) {
  const [apiKey, setApiKey] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = () => {
    const trimmedKey = apiKey.trim();

    if (!trimmedKey) {
      setError("API key cannot be empty");
      return;
    }

    if (!trimmedKey.startsWith("sk-ant-")) {
      setError("Invalid API key format. Must start with 'sk-ant-'");
      return;
    }

    setError("");
    onSubmit(trimmedKey);
    setApiKey("");
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSubmit();
    }
  };

  return (
    <Dialog open={open} onClose={() => {}} maxWidth="sm" fullWidth disableEscapeKeyDown>
      <DialogTitle>Enter Anthropic API Key</DialogTitle>
      <DialogContent sx={{ pt: 2 }}>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <Typography variant="body2" color="textSecondary">
            To use this app, you need an Anthropic API key. You can get one at{" "}
            <a href="https://console.anthropic.com" target="_blank" rel="noopener noreferrer">
              console.anthropic.com
            </a>
          </Typography>

          {error && <Alert severity="error">{error}</Alert>}

          <TextField
            autoFocus
            fullWidth
            label="API Key"
            type="password"
            placeholder="sk-ant-..."
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            onKeyPress={handleKeyPress}
            error={!!error}
            variant="outlined"
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleSubmit} variant="contained" color="primary">
          Continue
        </Button>
      </DialogActions>
    </Dialog>
  );
}
