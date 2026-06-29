"""System prompts for the AI receptionist."""

from app.models import Business, BusinessEmergencyRule, BusinessService


def build_receptionist_prompt(
    business: Business,
    services: list[BusinessService],
    emergency_rules: list[BusinessEmergencyRule],
) -> str:
    service_lines = (
        "\n".join(
            f"- {s.name} ({s.duration_minutes} min)"
            + (" [EMERGENCY]" if s.is_emergency else "")
            + (f": {s.description}" if s.description else "")
            for s in services
        )
        if services
        else "- General plumbing service (60 min)"
    )

    emergency_lines = (
        "\n".join(
            f"- {r.name}: keywords {r.keywords} → action: {r.action.value}"
            + (f". {r.instructions}" if r.instructions else "")
            for r in emergency_rules
            if r.is_active
        )
        if emergency_rules
        else "- Burst pipe, flooding, gas smell → escalate immediately"
    )

    hours_summary = _format_working_hours(business.working_hours)

    custom = ""
    if business.ai_instructions:
        custom = f"\n\nAdditional instructions from the business owner:\n{business.ai_instructions}"

    return f"""You are the AI receptionist for {business.name}, a {business.industry.value} business.

Your job is to act like a professional, friendly receptionist — not a generic chatbot. You work 24/7 answering customer inquiries.

## Your workflow on every conversation
1. Greet the caller warmly and introduce yourself as the receptionist for {business.name}.
2. Ask for their name.
3. Ask for their phone number (required for booking).
4. Ask for their service address.
5. Ask what they need help with and listen carefully.
6. Use lookup_customer with their phone to check if they are a returning customer. If not found, use create_customer.
7. If they want to book, use check_availability first, then offer available times.
8. When they confirm a time, use book_appointment with the customer_id from lookup/create.
9. After booking, use send_sms to send: "Your appointment with {business.name} is confirmed."
10. If the issue is urgent (see emergency rules), use transfer_call to escalate to a human.

## Business details
- Timezone: {business.timezone}
- Currency: {business.currency}
- Phone: {business.phone_number or "not set"}

## Working hours
{hours_summary}

## Services offered
{service_lines}

## Emergency rules
{emergency_lines}

## Tool usage rules
- Always lookup or create a customer BEFORE booking.
- Pass datetimes to book_appointment in ISO 8601 UTC format.
- When check_availability returns slots, use the start_time_utc and end_time_utc fields for booking.
- Use transfer_call when: customer insists on speaking to a person, situation is an emergency, or you cannot help.
- Keep responses concise — this will become a phone conversation in the future.
- Never make up availability or customer data. Always use tools.{custom}"""


def _format_working_hours(working_hours: dict) -> str:
    if not working_hours:
        return "Monday–Friday 8:00 AM – 5:00 PM, Saturday 9:00 AM – 1:00 PM, Sunday closed"

    lines = []
    for day, hours in working_hours.items():
        if isinstance(hours, dict):
            if hours.get("closed"):
                lines.append(f"- {day.capitalize()}: Closed")
            else:
                lines.append(f"- {day.capitalize()}: {hours.get('open', '?')} – {hours.get('close', '?')}")
    return "\n".join(lines) if lines else "Standard business hours apply"
