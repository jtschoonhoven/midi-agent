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
  onClose?: () => void;
  allowClose?: boolean;
}

export default function ApiKeyModal({ open, onSubmit, onClose, allowClose = false }: ApiKeyModalProps) {
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

  const handleClose = () => {
    if (allowClose && onClose) {
      setError("");
      setApiKey("");
      onClose();
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth disableEscapeKeyDown={!allowClose}>
      <DialogTitle>Sign In with Anthropic API Key</DialogTitle>
      <DialogContent sx={{ pt: 2 }}>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <Typography variant="body2" color="textSecondary">
            Sign in with your Anthropic API key to save your work and use AI features. You can get a key at{" "}
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
        {allowClose && (
          <Button onClick={handleClose} color="inherit">
            Continue exploring demo
          </Button>
        )}
        <Button onClick={handleSubmit} variant="contained" color="primary">
          Sign In
        </Button>
      </DialogActions>
    </Dialog>
  );
}
