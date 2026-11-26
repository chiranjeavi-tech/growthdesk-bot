        await query.edit_message_text(
            text=(
                "🆕 *New User Bonus*\n"
                f"Bonus Amount: *{format_amount(NEW_USER_BONUS_AMOUNT)}*\n"
                f"💰 *Wallet Balance:* *{format_amount(wallet['balance'])}*"
            ),
            reply_markup=build_unlocked_keyboard(),
            parse_mode="Markdown",
        )
    elif data.startswith("folder:"):
        parts = data.split(":")
        folder_key = parts[1]
        page = int(parts[2]) if len(parts) > 2 else 0
        folder_data = FOLDERS.get(folder_key)
        if folder_data:
            channels = get_folder_channels(folder_key)
            await query.edit_message_text(
                text=f"*{folder_data['title']}* ({len(channels)}/{MAX_CHANNELS_PER_FOLDER} channels)\n\nSelect a channel:",
                reply_markup=build_folder_keyboard(folder_key, page=page),
                parse_mode="Markdown",
            )
    elif data == "back_main":
        missing = await get_missing_channels(context, user_id)
        await show_gate(update, context, missing, edit=True)


async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    if isinstance(context.error, Conflict):
        print("Polling Conflict detected: another instance is using getUpdates.", flush=True)
        return
    print(f"Unhandled bot error: {context.error}", flush=True)


def schedule_promo_jobs(app):
    if app.job_queue is None:
        print("Warning: job_queue is None.", flush=True)
        return
    for idx, post_time in enumerate(AUTO_POST_TIMES):
        app.job_queue.run_daily(send_scheduled_promo, time=post_time, data=idx, name=f"promo_job_{idx}")


if __name__ == "__main__":
    start_health_server()
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("go", go_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("reaction", reaction_command))
    app.add_handler(CommandHandler("use", use_command))
    app.add_handler(CommandHandler("hub", hub_command))
    app.add_handler(CommandHandler("newcomer", newcomer_command))
    app.add_handler(CommandHandler("redeem", redeem_command))
    app.add_handler(CommandHandler("folders", folders_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_error_handler(global_error_handler)
    schedule_promo_jobs(app)
    print("Bot polling started...", flush=True)
    app.run_polling(drop_pending_updates=True)
    
