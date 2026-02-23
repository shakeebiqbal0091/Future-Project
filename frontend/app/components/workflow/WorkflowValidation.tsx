import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';

interface WorkflowValidationProps {
  isValid: boolean;
  errors: string[];
  className?: string;
}

const WorkflowValidation: React.FC<WorkflowValidationProps> = ({ isValid, errors, className }) => {
  const [isDialogOpen, setIsDialogOpen] = React.useState(false);

  const handleShowErrors = () => {
    setIsDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setIsDialogOpen(false);
  };

  return (
    <div className={className}>
      <Card className="bg-red-50 border-red-200">
        <CardContent className="p-3">
          <div className="flex items-center gap-2">
            <Badge
              variant={isValid ? 'success' : 'destructive'}
              className="p-2"
            >
              {isValid ? 'Valid' : 'Invalid'}
            </Badge>

            {!isValid && (
              <div className="flex-1">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleShowErrors}
                  className="text-red-600 hover:bg-red-50"
                >
                  View {errors.length} Error{errors.length > 1 ? 's' : ''}
                </Button>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Error Dialog */}
      {!isValid && (
        <Dialog open={isDialogOpen} onOpenChange={handleCloseDialog}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Workflow Validation Errors</DialogTitle>
              <DialogDescription>Fix these issues before saving or running the workflow</DialogDescription>
            </DialogHeader>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {errors.map((error, index) => (
                <div key={index} className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-md">
                  <div className="flex-shrink-0">
                    <div className="w-2 h-2 bg-red-400 rounded-full mt-1"></div>
                  </div>
                  <p className="text-sm text-red-800 flex-1">{error}</p>
                </div>
              ))}
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
};

export default WorkflowValidation;