"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { GripVertical, Plus, Trash2, Edit3 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { TripDay, TripActivity, TripActivityType } from "@/types/trip";
import { activityTypeLabels, activityTypeEmojis } from "@/types/trip";

type Props = {
  day: TripDay;
  dayIndex: number;
  onUpdate: (day: TripDay) => void;
  onRemove: (dayId: string) => void;
};

export default function DayCard({ day, dayIndex, onUpdate, onRemove }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [editTitle, setEditTitle] = useState(day.title);

  const handleTitleSave = () => {
    if (editTitle.trim() && editTitle !== day.title) {
      onUpdate({ ...day, title: editTitle });
    }
    setEditMode(false);
  };

  return (
    <motion.div
      layout
      className="rounded-2xl border border-gray-100 bg-white shadow-sm"
    >
      <div className="flex items-center gap-3 p-4">
        <div
          className="cursor-grab rounded-lg p-1 text-gray-400 hover:bg-gray-50 active:cursor-grabbing"
          aria-label="Drag to reorder day"
        >
          <GripVertical className="h-5 w-5" />
        </div>

        <div className="flex-1">
          {editMode ? (
            <input
              type="text"
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              onBlur={handleTitleSave}
              onKeyDown={(e) => e.key === "Enter" && handleTitleSave()}
              className="text-lg font-semibold text-dark outline-none"
              autoFocus
            />
          ) : (
            <h3 className="text-lg font-semibold text-dark">{day.title}</h3>
          )}
          <p className="text-sm text-gray-500">{day.date}</p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setEditMode(!editMode)}
            className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            aria-label={editMode ? "Cancel edit" : "Edit title"}
          >
            <Edit3 className="h-4 w-4" />
          </button>
          <button
            onClick={() => setExpanded(!expanded)}
            className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            aria-label={expanded ? "Collapse" : "Expand"}
          >
            <svg
              className={cn("h-4 w-4 transition-transform", expanded && "rotate-180")}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          <button
            onClick={() => onRemove(day.id)}
            className="rounded-lg p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600"
            aria-label="Remove day"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden border-t border-gray-100"
          >
            <div className="p-4">
              <div
                className="mb-3 flex items-center justify-between"
                style={{ display: "flex" }}
              >
                <h4 className="text-sm font-semibold text-dark">Activities</h4>
              </div>

              {day.activities.length === 0 ? (
                <button
                  onClick={() => onUpdate({ ...day, activities: [...day.activities, { id: crypto.randomUUID(), type: "custom", title: "New Activity", description: "", time: "12:00", duration: "1h", notes: "" }] })}
                  className="flex w-full items-center justify-center gap-2 rounded-xl border-2 border-dashed border-gray-200 py-3 text-sm text-gray-500 transition-colors hover:border-primary hover:text-primary"
                >
                  <Plus className="h-4 w-4" />
                  Add Activity
                </button>
              ) : (
                <div className="space-y-2">
                  {day.activities.map((activity) => (
                    <ActivityItem
                      key={activity.id}
                      activity={activity}
                      onUpdate={(updated) => {
                        onUpdate({
                          ...day,
                          activities: day.activities.map((a) => (a.id === activity.id ? updated : a)),
                        });
                      }}
                      onRemove={() => {
                        onUpdate({
                          ...day,
                          activities: day.activities.filter((a) => a.id !== activity.id),
                        });
                      }}
                    />
                  ))}
                </div>
              )}

              <button
                onClick={() => onUpdate({ ...day, activities: [...day.activities, { id: crypto.randomUUID(), type: "custom", title: "New Activity", description: "", time: "12:00", duration: "1h", notes: "" }] })}
                className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl border border-gray-200 py-2 text-sm text-gray-600 transition-colors hover:border-primary hover:text-primary"
              >
                <Plus className="h-4 w-4" />
                Add Activity
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

type ActivityProps = {
  activity: TripActivity;
  onUpdate: (activity: TripActivity) => void;
  onRemove: () => void;
};

function ActivityItem({ activity, onUpdate, onRemove }: ActivityProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <motion.div
      layout
      className="rounded-xl border border-gray-100 bg-gray-50/50 p-3"
    >
      <div className="flex items-center gap-3">
        <span className="text-xl">{activityTypeEmojis[activity.type]}</span>
        <div className="flex-1">
          <input
            type="text"
            value={activity.title}
            onChange={(e) => onUpdate({ ...activity, title: e.target.value })}
            className="text-sm font-medium text-dark outline-none"
            placeholder="Activity title"
          />
          <div className="mt-1 flex gap-3 text-xs text-gray-500">
            <input
              type="time"
              value={activity.time}
              onChange={(e) => onUpdate({ ...activity, time: e.target.value })}
              className="w-16 text-dark outline-none"
            />
            <input
              type="text"
              value={activity.duration}
              onChange={(e) => onUpdate({ ...activity, duration: e.target.value })}
              className="w-12 text-dark outline-none"
              placeholder="Duration"
            />
          </div>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="rounded-lg p-1 text-gray-400 hover:bg-gray-200/50"
          aria-label={expanded ? "Collapse" : "Expand"}
        >
          <svg
            className={cn("h-4 w-4 transition-transform", expanded && "rotate-180")}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="mt-2 overflow-hidden"
          >
            <textarea
              value={activity.description || ""}
              onChange={(e) => onUpdate({ ...activity, description: e.target.value })}
              placeholder="Description (optional)"
              className="mt-2 w-full resize-y rounded-lg border border-gray-200 bg-white px-2.5 py-2 text-xs text-gray-600 outline-none focus:border-primary"
              rows={2}
            />
            <textarea
              value={activity.notes || ""}
              onChange={(e) => onUpdate({ ...activity, notes: e.target.value })}
              placeholder="Notes (optional)"
              className="mt-2 w-full resize-y rounded-lg border border-gray-200 bg-white px-2.5 py-2 text-xs text-gray-600 outline-none focus:border-primary"
              rows={2}
            />
            <select
              value={activity.type}
              onChange={(e) =>
                onUpdate({ ...activity, type: e.target.value as TripActivityType })
              }
              className="mt-2 w-full rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-xs text-dark outline-none focus:border-primary"
            >
              {Object.entries(activityTypeLabels).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            <button
              onClick={onRemove}
              className="mt-2 flex w-full items-center justify-center gap-1 rounded-lg py-1.5 text-xs text-red-600 hover:bg-red-50"
            >
              <Trash2 className="h-3 w-3" />
              Remove Activity
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
