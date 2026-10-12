## 🌦️ Summary

Version 0.2.0 makes virtual Weather Underground stations easier to validate,
maintain, and troubleshoot through native Home Assistant workflows.

## ✨ Highlights

- Validate credentials and current observations with a dedicated test-upload
  control that does not alter normal operational state.
- Manage each station as a stable Home Assistant device and reconfigure its
  Station ID or Station Key without losing mappings.
- Detect unusable mapped entities, inspect their exact problem type, and repair
  persistent failures through Home Assistant Repairs.
- Map numeric helpers and template sensors without vendor restrictions and set
  the maximum accepted source age independently for each station.

## ⚠️ Breaking changes

- The upload interval is now configured in minutes rather than seconds.
- New stations default to a 30-minute upload interval.
- Existing missing and 300-second interval values migrate to 30 minutes.
- Other existing interval values round up to the next 5-minute increment and
  clamp to the supported 5-to-1,440-minute range.
